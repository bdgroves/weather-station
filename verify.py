"""How good is the forecast? Scores daily high/low forecasts against what was measured.

Forecasts
  - Open-Meteo, the model the page shows: its Previous Runs archive gives what it forecast
    1-7 days ahead for every hour since mid-March 2026, so the score starts with months of history.
  - The National Weather Service's own forecast: nobody archives it in a form we can reach, so
    save_nws() keeps one issue a day (the first run after 6 am local) in data/nws_forecasts.json.
Truth: each station's daily high and low (midnight to midnight local, except co-op stations, which
  report once a day at their observer's time).
Baselines a forecast has to beat: "it will be the normal for the date" and "same as N days ago".

Writes data/verify.json; stdlib only.
"""
import datetime as dt
import json
import math
import os
import urllib.parse
from zoneinfo import ZoneInfo

OUT = os.path.join(os.path.dirname(__file__), "data")
NWS_FILE = os.path.join(OUT, "nws_forecasts.json")
VERIFY_FILE = os.path.join(OUT, "verify.json")
VERSION = 2
LEADS = range(1, 8)

# Where each home station's daily high/low comes from: the station closest to the forecast point
# with a complete daily record (ACIS stopped receiving McChord's daily summaries in September 2026).
TRUTH = {
    "lakewood_wa": {"src": "iem", "station": "TCM", "network": "WA_ASOS", "label": "McChord AFB (KTCM)"},
    # Columbia airport, 3 miles from Sonora: an automated station that reports every day. The Sonora co-op
    # station misses about a third of days and logged a week of faulty lows in September 2026.
    "sonora_ca": {"src": "iem", "station": "O22", "network": "CA_ASOS", "label": "Columbia airport (O22), 3 miles from Sonora"},
    "reno_nv": {"src": "iem", "station": "RNO", "network": "NV_ASOS", "label": "Reno–Tahoe airport (KRNO)"},
    "death_valley_ca": {"src": "acis", "sid": "042319 2", "label": "Death Valley (Furnace Creek)"},
}


def _get(get, url, params=None, accept="application/json"):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    return get(url, accept=accept)


# ── forecasts ────────────────────────────────────────────────────────────────
def model_forecasts(get, st, start, end):
    """{lead: {date: (hi, lo)}} from Open-Meteo's archive of its own past forecasts."""
    hourly = ",".join(f"temperature_2m_previous_day{n}" for n in LEADS)
    j = _get(get, "https://previous-runs-api.open-meteo.com/v1/forecast",
             {"latitude": st["lat"], "longitude": st["lon"], "hourly": hourly, "temperature_unit": "fahrenheit",
              "timezone": st["tz"], "start_date": start.isoformat(), "end_date": end.isoformat()})
    h = j.get("hourly") or {}
    times = h.get("time") or []
    out = {}
    for n in LEADS:
        vals = h.get(f"temperature_2m_previous_day{n}") or []
        by = {}
        for t, v in zip(times, vals):
            if v is not None:
                by.setdefault(t[:10], []).append(v)
        out[n] = {d: (round(max(v), 1), round(min(v), 1)) for d, v in by.items() if len(v) >= 20}
    return out


def save_nws(get, st, now_utc):
    """Keep the day's NWS forecast (first run after 6 am local). Returns True if the archive changed."""
    tz = ZoneInfo(st["tz"])
    local = now_utc.astimezone(tz)
    if local.hour < 6:
        return False
    arch = json.load(open(NWS_FILE)) if os.path.exists(NWS_FILE) else {"stations": {}}
    mine = arch["stations"].setdefault(st["key"], {})
    issue = local.date().isoformat()
    if issue in mine:
        return False
    pts = get(f"https://api.weather.gov/points/{st['lat']},{st['lon']}")["properties"]
    periods = get(pts["forecast"])["properties"]["periods"]
    days = {}
    for p in periods:
        if p.get("temperature") is None:
            continue
        t = p["temperature"] if p.get("temperatureUnit", "F") == "F" else p["temperature"] * 9 / 5 + 32
        d = dt.datetime.fromisoformat(p["startTime"]).astimezone(tz).date()
        if p.get("isDaytime"):
            days.setdefault(d.isoformat(), {})["hi"] = t
        else:   # tonight's low is the next morning's
            days.setdefault((d + dt.timedelta(days=1)).isoformat(), {})["lo"] = t
    mine[issue] = {"issued": now_utc.isoformat(timespec="minutes"), "days": days}
    cutoff = (local.date() - dt.timedelta(days=200)).isoformat()
    for k in [k for k in mine if k < cutoff]:
        del mine[k]
    with open(NWS_FILE, "w") as f:
        json.dump(arch, f, separators=(",", ":"), sort_keys=True)
    return True


def nws_forecasts(key):
    """{lead: {date: (hi, lo)}} from the saved NWS issues."""
    arch = json.load(open(NWS_FILE)) if os.path.exists(NWS_FILE) else {"stations": {}}
    out = {n: {} for n in LEADS}
    for issue, rec in arch["stations"].get(key, {}).items():
        i = dt.date.fromisoformat(issue)
        for d, v in rec["days"].items():
            n = (dt.date.fromisoformat(d) - i).days
            if n in out:
                out[n][d] = (v.get("hi"), v.get("lo"))
    return out


# ── truth ────────────────────────────────────────────────────────────────────
def observed(get, key, start, end):
    """{date: (hi, lo)} measured."""
    t = TRUTH[key]
    out = {}
    if t["src"] == "acis":
        j = get("https://data.rcc-acis.org/StnData", data={"sid": t["sid"], "sdate": start.isoformat(), "edate": end.isoformat(),
                                                            "elems": "maxt,mint"}, accept="application/json")
        for d, a, b in j.get("data", []):
            hi, lo = _num(a), _num(b)
            if hi is not None and lo is not None:
                out[d] = (hi, lo)
    else:
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            j = _get(get, "https://mesonet.agron.iastate.edu/api/1/daily.json", {"station": t["station"], "network": t["network"], "year": y, "month": m})
            for r in j.get("data", []):
                hi, lo = r.get("max_tmpf"), r.get("min_tmpf")
                if r.get("date") and hi is not None and lo is not None and start.isoformat() <= r["date"] <= end.isoformat():
                    out[r["date"]] = (float(hi), float(lo))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _num(v):
    try:
        return float(str(v).rstrip("ASTa"))
    except ValueError:
        return None


# ── scoring ──────────────────────────────────────────────────────────────────
def _stats(errs):
    if not errs:
        return None
    a = sorted(abs(e) for e in errs)
    p80 = a[min(len(a) - 1, math.ceil(0.8 * len(a)) - 1)]
    return {"mae": round(sum(a) / len(a), 1), "bias": round(sum(errs) / len(errs), 1), "p80": round(p80, 1), "n": len(errs)}


def score(obs, fc, normals, dates):
    """Per lead: errors (forecast - observed) of the high and low for model, nws, normal, persistence."""
    res = {}
    for n in LEADS:
        row = {}
        for name, src in (("model", fc["model"]), ("nws", fc["nws"])):
            row[name] = {k: _stats([src[n][d][i] - obs[d][i] for d in dates if d in src[n] and src[n][d][i] is not None])
                         for i, k in ((0, "hi"), (1, "lo"))}
        row["normal"] = {k: _stats([normals[d[5:]][i] - obs[d][i] for d in dates if normals.get(d[5:]) and normals[d[5:]][i] is not None])
                         for i, k in ((0, "hi"), (1, "lo"))}
        prev = lambda d: (dt.date.fromisoformat(d) - dt.timedelta(days=n)).isoformat()
        row["persistence"] = {k: _stats([obs[prev(d)][i] - obs[d][i] for d in dates if prev(d) in obs]) for i, k in ((0, "hi"), (1, "lo"))}
        res[n] = row
    return res


def build(get, stations, climate):
    """Score every home station. Returns the verify.json document."""
    doc = {"version": VERSION, "built": None, "stations": {}}
    for st in stations:
        key = st["key"]
        try:
            today = dt.datetime.now(ZoneInfo(st["tz"])).date()
            end = today - dt.timedelta(days=1)
            start = today - dt.timedelta(days=200)
            fc = {"model": model_forecasts(get, st, start, end), "nws": nws_forecasts(key)}
            obs = observed(get, key, start - dt.timedelta(days=7), end)
            days = (climate.get("stations", {}).get(key) or {}).get("days", {})
            normals = {md: (v.get("normal_hi"), v.get("normal_lo")) for md, v in days.items()}
            first_model = min((d for d in fc["model"][1]), default=None)
            dates = sorted(d for d in obs if first_model and first_model <= d <= end.isoformat())
            last30 = [d for d in dates if d > (end - dt.timedelta(days=30)).isoformat()]
            series = []
            for d in dates[-45:]:
                g = lambda src, n, i: (src[n].get(d) or (None, None))[i]
                series.append({"date": d, "obs_hi": obs[d][0], "obs_lo": obs[d][1],
                               "m1_hi": g(fc["model"], 1, 0), "m3_hi": g(fc["model"], 3, 0), "m5_hi": g(fc["model"], 5, 0),
                               "m1_lo": g(fc["model"], 1, 1), "nws1_hi": g(fc["nws"], 1, 0),
                               "normal_hi": (normals.get(d[5:]) or (None, None))[0], "normal_lo": (normals.get(d[5:]) or (None, None))[1]})
            nws_issues = sorted(json.load(open(NWS_FILE))["stations"].get(key, {})) if os.path.exists(NWS_FILE) else []
            doc["stations"][key] = {
                "truth": TRUTH[key]["label"], "first": dates[0] if dates else None, "last": dates[-1] if dates else None,
                "days": len(dates), "nws_since": nws_issues[0] if nws_issues else None,
                "all": score(obs, fc, normals, dates), "last30": score(obs, fc, normals, last30), "series": series}
            m = doc["stations"][key]["all"][1]["model"]["hi"]
            print(f"  verify {st['name']}: {len(dates)} days, day-1 high off by {m and m['mae']}° on average")
        except Exception as e:
            print(f"  verify {st['name']} failed: {e}")
    return doc
