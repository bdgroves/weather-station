"""Probe: IEM active VTEC events (county/zone geojson): size, fields, and whether Sonora's Heat Advisory is there."""
import json, requests
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Origin": "https://brooksgroves.com"}
out = {}
r = requests.get("https://mesonet.agron.iastate.edu/api/1/vtec/county_zone.geojson", headers=H, timeout=90)
out["bytes"] = len(r.content); out["enc"] = r.headers.get("Content-Encoding"); out["ctype"] = r.headers.get("Content-Type")
j = r.json(); fs = j["features"]; out["n"] = len(fs)
out["props_keys"] = list(fs[0]["properties"].keys()) if fs else None
sto = [f for f in fs if f["properties"].get("wfo") == "STO"]
out["sto"] = [{k: f["properties"].get(k) for k in ("ph_sig", "ugc", "name", "utc_issue", "utc_expire", "eventid", "phenomena", "significance")} | {"geomtype": (f.get("geometry") or {}).get("type")} for f in sto][:12]
out["sample"] = fs[0]["properties"] if fs else None
# also try sbw (storm based) active
r2 = requests.get("https://mesonet.agron.iastate.edu/api/1/vtec/sbw_interval.geojson", headers=H, timeout=60)
out["sbw_status"] = r2.status_code; out["sbw_body"] = r2.text[:300]
# events by point with other date params
r3 = requests.get("https://mesonet.agron.iastate.edu/json/vtec_events_bypoint.py", params={"lat": 37.9841, "lon": -120.3822, "sdate": "2026-01-01", "edate": "2026-12-31"}, headers=H, timeout=60)
out["bypoint_year"] = r3.text[:600]
r4 = requests.get("https://mesonet.agron.iastate.edu/json/vtec_events_byugc.py", params={"ugc": "CAZ068", "sdate": "2026-09-01", "edate": "2026-10-31"}, headers=H, timeout=60)
out["byugc"] = r4.text[:600]
json.dump(out, open("tools/probe_out.json", "w"), indent=1)
