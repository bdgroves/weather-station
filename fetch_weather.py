#!/usr/bin/env python3
"""
Weather Station — fetch_weather.py
───────────────────────────────────────────────────────────────────────────────
The page reads live data straight from the sources in the browser (NWS
observations, alerts and forecasts; Open-Meteo forecasts and air quality), so
it is never older than a few minutes. This script does the slow and heavy
work once an hour in GitHub Actions:

  data/weather.json   a snapshot of everything, used only if a live source
                      fails (and by anything else that wants one file)
  data/climate.json   for each station's long-record climate site (ACIS):
                      record high/low for every day of the year with the year
                      it happened, 1991–2020 normals, and this month and this
                      water year against normal. Rebuilt daily.

Observed vs modelled: "current conditions" used to be Open-Meteo's model
estimate for the grid square. They are now the latest real observation from
the nearest NWS station, and the model is shown beside it as a forecast.

Python 3.12 stdlib only.
"""

import datetime as dt
import json
import math
import os
import time
import urllib.request

UA = "WeatherStation/2.0 (github.com/bdgroves/weather-station)"
OUT = os.path.join(os.path.dirname(__file__), "data")

# obs: NWS observation stations, best first. climate: ACIS station with the long record.
STATIONS = [
    {"key": "lakewood_wa", "name": "Lakewood", "state": "WA", "lat": 47.1718, "lon": -122.5185, "elevation_ft": 300,
     "tz": "America/Los_Angeles", "nws": "SEW", "obs": ["KTCM", "KTIW", "KPLU"],
     "climate": {"sid": "SEAthr 9", "label": "Sea-Tac Airport"}},
    {"key": "sonora_ca", "name": "Sonora", "state": "CA", "lat": 37.9841, "lon": -120.3822, "elevation_ft": 1785,
     "tz": "America/Los_Angeles", "nws": "STO", "obs": ["GNSC1", "MOUC1"],
     "obs_note": "Sonora has no NWS observing station. The readings come from the Green Spring fire-weather station, 12 miles away and about 700 ft lower.",
     "climate": {"sid": "048353 2", "label": "Sonora"}},
    {"key": "reno_nv", "name": "Reno", "state": "NV", "lat": 39.5296, "lon": -119.8138, "elevation_ft": 4505,
     "tz": "America/Los_Angeles", "nws": "REV", "obs": ["KRNO"],
     "climate": {"sid": "RNOthr 9", "label": "Reno (airport and earlier city records)"}},
    {"key": "death_valley_ca", "name": "Death Valley", "state": "CA", "lat": 36.4620, "lon": -116.8666, "elevation_ft": -190,
     "tz": "America/Los_Angeles", "nws": "VEF", "obs": ["DEVC1"],
     "climate": {"sid": "042319 2", "label": "Death Valley (Furnace Creek / Greenland Ranch)"}},
]

WMO = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
       61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
       71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Showers", 81: "Showers",
       82: "Violent showers", 85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorm",
       96: "Thunderstorm, hail", 99: "Thunderstorm, heavy hail"}


def get(url, data=None, accept="application/geo+json", retries=3):
    body = json.dumps(data).encode() if data is not None else None
    hdr = {"User-Agent": UA, "Accept": accept}
    if body:
        hdr["Content-Type"] = "application/json"
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=hdr), timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"    retry {url[:60]}… ({e})")
            time.sleep(4 * (i + 1))


# ── Observations (NWS) ───────────────────────────────────────────────────────
def c2f(c):
    return None if c is None else round(c * 9 / 5 + 32, 1)


def latest_obs(st):
    for sid in st["obs"]:
        try:
            # the newest report can be partial (no temperature), so take the newest complete one of the last few
            feats = get(f"https://api.weather.gov/stations/{sid}/observations?limit=15")["features"]
            full = [f["properties"] for f in feats if (f["properties"].get("temperature") or {}).get("value") is not None]
            if not full:
                continue
            p = dict(full[0])
            for k in ("seaLevelPressure", "barometricPressure", "visibility"):   # short reports between hourly ones lack these
                if (p.get(k) or {}).get("value") is None:
                    p[k] = next((f["properties"][k] for f in feats if (f["properties"].get(k) or {}).get("value") is not None), None)
            v = lambda k: (p.get(k) or {}).get("value")
            return {"station": sid, "name": p.get("stationName"), "time": p.get("timestamp"),
                    "text": p.get("textDescription") or None, "temp": c2f(v("temperature")),
                    "dewpoint": c2f(v("dewpoint")), "humidity": round(v("relativeHumidity")) if v("relativeHumidity") is not None else None,
                    "wind_mph": round(v("windSpeed") / 1.609, 1) if v("windSpeed") is not None else None,
                    "gust_mph": round(v("windGust") / 1.609, 1) if v("windGust") is not None else None,
                    "wind_dir": v("windDirection"),
                    "pressure_hpa": round((v("seaLevelPressure") or v("barometricPressure")) / 100, 1) if (v("seaLevelPressure") or v("barometricPressure")) else None,
                    "visibility_mi": round(v("visibility") / 1609.34, 1) if v("visibility") is not None else None,
                    "heat_index": c2f(v("heatIndex")), "wind_chill": c2f(v("windChill"))}
        except Exception as e:
            print(f"    obs {sid}: {e}")
    return None


# ── Forecast snapshot (Open-Meteo) — fallback for the page ───────────────────
def forecast(st):
    hourly = "temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl,relative_humidity_2m,uv_index"
    daily = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,sunrise,sunset,uv_index_max"
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={st['lat']}&longitude={st['lon']}"
           f"&current=temperature_2m,weather_code,wind_speed_10m,pressure_msl&hourly={hourly}&daily={daily}"
           f"&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone={st['tz']}"
           f"&forecast_days=7&past_hours=24")
    d = get(url, accept="application/json")
    d["current"]["weather_text"] = WMO.get(d["current"].get("weather_code"), "")
    return {"current": d["current"], "hourly": d["hourly"], "daily": d["daily"],
            "utc_offset_seconds": d.get("utc_offset_seconds")}


def alerts(st):
    try:
        feats = get(f"https://api.weather.gov/alerts/active?point={st['lat']},{st['lon']}&status=actual")["features"]
        return [{"event": f["properties"]["event"], "severity": f["properties"]["severity"],
                 "headline": f["properties"]["headline"], "expires": f["properties"]["expires"],
                 "description": (f["properties"].get("description") or "")[:1500]} for f in feats]
    except Exception as e:
        print(f"    alerts: {e}")
        return []


# ── Climate (ACIS) ───────────────────────────────────────────────────────────
def acis_val(v):
    """ACIS strings: '72', 'M' missing, 'T' trace, '0.42A' accumulated, 'S' subsequent."""
    if v in ("M", "S", "", None):
        return None
    if v == "T":
        return 0.0
    try:
        return float(v.rstrip("ASTa"))
    except ValueError:
        return None


def freeze_stats(days, thresh=32.0):
    """First fall and last spring freeze (low at or below 32°F) for every season with a nearly complete record.

    A season runs July 1 to June 30. Fall: the first freeze after July 1; spring: the last before July 1.
    Dates are kept as days since July 1 so they average and rank across the new year.
    Returns medians, 10th/90th percentiles, extremes with years, the share of seasons with no freeze,
    the chance of a first freeze by each date (for the odds curve), and this season so far.
    """
    by = {}
    for date, mx, mn, pc, sn in days:
        d = dt.date.fromisoformat(date)
        season = d.year if d.month >= 7 else d.year - 1
        by.setdefault(season, []).append((d, mn))
    today = dt.date.today()
    cur = today.year if today.month >= 7 else today.year - 1
    first, last, nofreeze = [], [], 0
    for season, rows in sorted(by.items()):
        if season >= cur:
            continue
        rep = [r for r in rows if r[1] is not None]
        if len(rep) < 0.9 * 365:          # too many missing days to trust a first or last date
            continue
        start = dt.date(season, 7, 1)
        fr = [d for d, mn in rep if mn <= thresh]
        fall = [d for d in fr if d.month >= 7]
        spring = [d for d in fr if d.month < 7]
        if not fr:
            nofreeze += 1
            continue
        if fall:
            first.append(((min(fall) - start).days, season))
        if spring:
            last.append(((max(spring) - dt.date(season + 1, 1, 1)).days, season + 1))
    n = len(first) + nofreeze
    if n < 10:
        return None

    def md_from(off, base_year=2001):   # day offset from July 1 → "MM-DD"
        return (dt.date(base_year, 7, 1) + dt.timedelta(days=off)).strftime("%m-%d")

    def md_from_jan(off):
        return (dt.date(2001, 1, 1) + dt.timedelta(days=off)).strftime("%m-%d")

    def pct(vals, p):
        v = sorted(vals)
        return v[min(len(v) - 1, max(0, round(p * (len(v) - 1))))]

    out = {"n_seasons": n, "no_freeze_pct": round(100 * nofreeze / n), "threshold": thresh}
    if first:
        offs = [o for o, _ in first]
        e, l = min(first), max(first)
        out["first"] = {"median": md_from(pct(offs, .5)), "p10": md_from(pct(offs, .1)), "p90": md_from(pct(offs, .9)),
                        "earliest": [md_from(e[0]), e[1] + (1 if md_from(e[0]) < "07-01" else 0)], "latest": [md_from(l[0]), l[1] + (1 if md_from(l[0]) < "07-01" else 0)]}
        # chance of at least one freeze by each week from Sept 1 to Feb 1 (share of all seasons, freezeless ones included)
        out["odds"] = [[md_from(o), round(100 * sum(1 for x in offs if x <= o) / n)] for o in range(62, 216, 7)]
    if last:
        offs = [o for o, _ in last]
        e, l = min(last), max(last)
        out["last"] = {"median": md_from_jan(pct(offs, .5)), "p10": md_from_jan(pct(offs, .1)), "p90": md_from_jan(pct(offs, .9)),
                       "earliest": [md_from_jan(e[0]), e[1]], "latest": [md_from_jan(l[0]), l[1]]}
    # this season so far
    rows = [(d, mn) for d, mn in by.get(cur, []) if mn is not None]
    fr = [d for d, mn in rows if mn <= thresh]
    out["this_season"] = {"first": fr[0].isoformat() if fr else None,
                          "lowest": min(((mn, d.isoformat()) for d, mn in rows), default=(None, None))}
    prev = [(d, mn) for d, mn in by.get(cur - 1, []) if mn is not None and d.month < 7 and mn <= thresh]
    out["last_spring"] = max(prev)[0].isoformat() if prev else None
    return out


def climate(st):
    sid = st["climate"]["sid"]
    today = dt.date.today()
    d = get("https://data.rcc-acis.org/StnData",
            {"sid": sid, "sdate": "por", "edate": today.isoformat(), "elems": "maxt,mint,pcpn,snow", "meta": "name,sids,ll,elev"},
            accept="application/json")
    rows = d.get("data", [])
    meta = d.get("meta", {})
    by_md = {}                                   # "MM-DD" → lists
    days = []
    for date, mx, mn, pc, sn in rows:
        md = date[5:]
        e = by_md.setdefault(md, {"hi": [], "lo": [], "pcpn": []})
        mx, mn, pc = acis_val(mx), acis_val(mn), acis_val(pc)
        y = int(date[:4])
        if mx is not None:
            e["hi"].append((mx, y))
        if mn is not None:
            e["lo"].append((mn, y))
        if pc is not None and 1991 <= y <= 2020:
            e["pcpn"].append(pc)
        days.append((date, mx, mn, pc, acis_val(sn)))

    keys = [f"{m:02d}-{dd:02d}" for m in range(1, 13) for dd in range(1, 32)
            if not (m in (4, 6, 9, 11) and dd == 31) and not (m == 2 and dd > 29)]

    def window(i, field, years=None):
        vals = []
        for k in range(i - 7, i + 8):
            for v, y in by_md.get(keys[k % len(keys)], {}).get(field, []):
                if years is None or years[0] <= y <= years[1]:
                    vals.append(v)
        return vals

    days_out = {}
    for i, k in enumerate(keys):
        e = by_md.get(k)
        if not e or not e["hi"]:
            continue
        nh, nl = window(i, "hi", (1991, 2020)), window(i, "lo", (1991, 2020))
        rh = max(e["hi"], key=lambda t: (t[0], t[1]))
        rl = min(e["lo"], key=lambda t: (t[0], -t[1])) if e["lo"] else (None, None)
        # mean daily precip, smoothed over ±7 days
        pv = [v for kk in range(i - 7, i + 8) for v in by_md.get(keys[kk % len(keys)], {}).get("pcpn", [])]
        days_out[k] = {"normal_hi": round(sum(nh) / len(nh), 1) if nh else None,
                       "normal_lo": round(sum(nl) / len(nl), 1) if nl else None,
                       "record_hi": rh[0], "record_hi_year": rh[1],
                       "record_lo": rl[0], "record_lo_year": rl[1],
                       "normal_pcpn": round(sum(pv) / len(pv), 3) if pv else None}

    freeze = freeze_stats(days)

    # recent daily values: last 400 days, for month-to-date and water-year-to-date
    recent = [{"date": a, "hi": b, "lo": c, "pcpn": p, "snow": s} for a, b, c, p, s in days[-400:]]
    first_year = int(rows[0][0][:4]) if rows else None
    return {"sid": sid, "label": st["climate"]["label"], "name": meta.get("name"), "elev_ft": meta.get("elev"),
            "first_year": first_year, "last_date": rows[-1][0] if rows else None,
            "days": days_out, "recent": recent, "freeze": freeze}


def moon():
    """Moon phase from the current instant (synodic month from a known new moon)."""
    now = dt.datetime.now(dt.timezone.utc)
    jd = now.timestamp() / 86400 + 2440587.5
    syn = 29.530588853
    age = (jd - 2451550.09766) % syn
    illum = (1 - math.cos(2 * math.pi * age / syn)) / 2
    names = ["New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", "Full Moon",
             "Waning Gibbous", "Last Quarter", "Waning Crescent"]
    return {"age_days": round(age, 2), "illumination": round(illum * 100, 1),
            "phase": names[int((age / syn) * 8 + 0.5) % 8],
            "days_to_full": round((syn / 2 - age) % syn, 1), "days_to_new": round(syn - age, 1)}


def main():
    os.makedirs(OUT, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    snap = {"generated_utc": now.isoformat(timespec="seconds"), "moon": moon(),
            "stations": {s["key"]: {k: s[k] for k in ("key", "name", "state", "lat", "lon", "elevation_ft", "tz", "nws", "obs")} | {"obs_note": s.get("obs_note")} for s in STATIONS}}
    ok = 0
    for st in STATIONS:
        print(f"{st['name']}, {st['state']}")
        rec = snap["stations"][st["key"]]
        try:
            rec["forecast"] = forecast(st)
            ok += 1
        except Exception as e:
            print(f"  forecast failed: {e}")
        rec["observed"] = latest_obs(st)
        try:
            rec["air_quality"] = get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={st['lat']}&longitude={st['lon']}"
                                     f"&current=us_aqi,pm2_5,pm10,ozone,us_aqi_pm2_5,us_aqi_ozone&hourly=us_aqi&timezone=auto&forecast_days=2",
                                     accept="application/json")
        except Exception as e:
            print(f"  air quality failed: {e}")
        rec["alerts"] = alerts(st)
        o = rec["observed"]
        print(f"  observed: {o and o['temp']}°F at {o and o['station']} ({o and o['time']}) · {len(rec['alerts'])} alerts")
    if not ok:
        print("::error::No forecasts fetched — keeping the published snapshot")
        raise SystemExit(1)
    with open(os.path.join(OUT, "weather.json"), "w") as f:
        json.dump(snap, f, separators=(",", ":"))

    # climate: once a day (ACIS updates overnight)
    cpath = os.path.join(OUT, "climate.json")
    old = json.load(open(cpath)) if os.path.exists(cpath) else {}
    labels_changed = any(old.get("stations", {}).get(st["key"], {}).get("label") != st["climate"]["label"] for st in STATIONS)
    missing_freeze = any("freeze" not in v for v in old.get("stations", {}).values())   # new field: rebuild once
    if old.get("built") != now.date().isoformat() or labels_changed or missing_freeze:
        clim = {"built": now.date().isoformat(), "stations": {}}
        for st in STATIONS:
            try:
                c = climate(st)
                clim["stations"][st["key"]] = c
                print(f"  climate {st['name']}: {c['name']} since {c['first_year']}, through {c['last_date']}")
            except Exception as e:
                print(f"  climate {st['name']} failed: {e}")
                if st["key"] in old.get("stations", {}):
                    clim["stations"][st["key"]] = old["stations"][st["key"]]
        if clim["stations"]:
            with open(cpath, "w") as f:
                json.dump(clim, f, separators=(",", ":"))

    # forecast scoring: save today's NWS forecast (once a day), and re-score once a day after the
    # overnight station reports are in (9 am Pacific); a new scoring version rebuilds straight away
    import verify
    from zoneinfo import ZoneInfo
    for st in STATIONS:
        try:
            if verify.save_nws(get, st, now):
                print(f"  saved today's NWS forecast for {st['name']}")
        except Exception as e:
            print(f"  NWS forecast archive {st['name']} failed: {e}")
    local = now.astimezone(ZoneInfo("America/Los_Angeles"))
    vold = json.load(open(verify.VERIFY_FILE)) if os.path.exists(verify.VERIFY_FILE) else {}
    if vold.get("version") != verify.VERSION or (vold.get("built") != local.date().isoformat() and local.hour >= 9):
        clim_now = json.load(open(cpath)) if os.path.exists(cpath) else {}
        doc = verify.build(get, STATIONS, clim_now)
        doc["built"] = local.date().isoformat()
        for k, v in vold.get("stations", {}).items():   # keep yesterday's score for a station that failed today
            doc["stations"].setdefault(k, v)
        if doc["stations"]:
            with open(verify.VERIFY_FILE, "w") as f:
                json.dump(doc, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
