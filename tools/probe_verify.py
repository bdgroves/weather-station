"""Probe: Open-Meteo Previous Runs API (past forecasts by lead day) and ACIS daily truth stations."""
import json, requests, datetime as dt
out = {}
today = dt.date.today()
url = "https://previous-runs-api.open-meteo.com/v1/forecast"
p = {"latitude": 47.1718, "longitude": -122.5185, "hourly": ",".join(["temperature_2m"] + [f"temperature_2m_previous_day{i}" for i in range(1, 8)]),
     "temperature_unit": "fahrenheit", "timezone": "America/Los_Angeles", "start_date": (today - dt.timedelta(days=200)).isoformat(), "end_date": (today - dt.timedelta(days=1)).isoformat()}
r = requests.get(url, params=p, timeout=90)
out["om_status"] = r.status_code
try:
    j = r.json(); h = j.get("hourly", {})
    out["om_keys"] = list(h.keys()); t = h.get("time", [])
    out["om_n"] = len(t); out["om_first"] = t[:1]; out["om_last"] = t[-1:]
    for k in h:
        if k != "time":
            vals = h[k]; first = next((i for i, v in enumerate(vals) if v is not None), None)
            out[f"om_first_nonnull_{k}"] = t[first] if first is not None else None
    out["om_err"] = j.get("reason")
except Exception as e:
    out["om_err"] = str(e)[:300] + r.text[:300]
# ACIS truth candidates
for name, sid in [("mcchord", "TCM 3"), ("seatac", "SEA 3"), ("reno", "RNO 3"), ("sonora", "048353 2"), ("dv", "042319 2"), ("gnsc1", "GNSC1 7"), ("devc1", "DEVC1 7")]:
    try:
        d = requests.get("https://data.rcc-acis.org/StnData", params={"sid": sid, "sdate": (today - dt.timedelta(days=6)).isoformat(), "edate": today.isoformat(), "elems": "maxt,mint", "meta": "name,sids,valid_daterange"}, timeout=60).json()
        out["acis_" + name] = {"meta": d.get("meta"), "data": d.get("data"), "error": d.get("error")}
    except Exception as e:
        out["acis_" + name] = str(e)[:200]
# obs time for coop stations
try:
    d = requests.get("https://data.rcc-acis.org/StnData", params={"sid": "048353 2", "sdate": (today - dt.timedelta(days=3)).isoformat(), "edate": today.isoformat(), "elems": json.dumps([{"name": "maxt", "add": "t"}, {"name": "mint", "add": "t"}])}, timeout=60).json()
    out["sonora_obstime"] = d.get("data")
except Exception as e:
    out["sonora_obstime"] = str(e)[:200]
json.dump(out, open("tools/probe_out.json", "w"), indent=0)
