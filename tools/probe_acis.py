"""Probe: ACIS stations near searched places, with temperature and precipitation date ranges."""
import json, math, requests
out = {}
for name, lat, lon in [("lawton", 34.609, -98.39), ("moab", 38.573, -109.55), ("bend", 44.058, -121.315)]:
    d = 0.45
    r = requests.get("https://data.rcc-acis.org/StnMeta", params={"bbox": f"{lon-d:.2f},{lat-d:.2f},{lon+d:.2f},{lat+d:.2f}", "elems": "maxt,mint,pcpn", "meta": "name,uid,ll,elev,valid_daterange,sids"}, timeout=60).json()
    rows = []
    for m in r.get("meta", []):
        mi = math.hypot((m["ll"][0]-lon)*math.cos(math.radians(lat)), m["ll"][1]-lat)*69
        rows.append([round(mi, 1), m["name"], m.get("uid"), m.get("valid_daterange"), (m.get("sids") or [""])[0]])
    out[name] = sorted([x for x in rows if x[3] and x[3][0]], key=lambda x: x[0])[:25]
json.dump(out, open("tools/probe_out.json", "w"), indent=0)
