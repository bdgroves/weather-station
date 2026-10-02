"""Probe: pressure fields in the last 30 h of observations for each station."""
import json, datetime as dt, requests
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Accept": "application/geo+json"}
start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
out = {}
for sid in ["KTCM", "MOUC1", "KRNO", "DEVC1"]:
    try:
        fs = requests.get(f"https://api.weather.gov/stations/{sid}/observations?start={start}", headers=H, timeout=60).json()["features"]
        rows = []
        for f in fs:
            p = f["properties"]; g = lambda k: (p.get(k) or {}).get("value")
            rows.append([p["timestamp"][5:16], g("seaLevelPressure"), g("barometricPressure"), g("temperature"), (p.get("rawMessage") or "")[:12]])
        out[sid] = rows
    except Exception as e:
        out[sid] = str(e)
json.dump(out, open("tools/probe_out.json", "w"), indent=0)
