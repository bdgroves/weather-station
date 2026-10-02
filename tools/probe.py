"""Probe in Actions: NWS observation stations near each location, freshness, ACIS long-record stations, CORS."""
import json, traceback, math
import requests
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Accept": "application/geo+json"}
LOC = {"lakewood": (47.1718, -122.5185), "groveland": (37.8463, -120.2313), "reno": (39.5296, -119.8138), "death_valley": (36.4620, -116.8666)}
out = {}
def step(k, f):
    try: out[k] = f()
    except Exception: out[k] = {"error": traceback.format_exc()[-1200:]}
def dist(a, b):
    return 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(b[0]-a[0])/2)**2 + math.cos(math.radians(a[0]))*math.cos(math.radians(b[0]))*math.sin(math.radians(b[1]-a[1])/2)**2))
for k, (lat, lon) in LOC.items():
    def nws(lat=lat, lon=lon):
        p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=H, timeout=30)
        pj = p.json()["properties"]
        st = requests.get(pj["observationStations"], headers=H, timeout=30).json()["features"][:8]
        res = {"office": pj.get("gridId"), "grid": [pj.get("gridX"), pj.get("gridY")], "forecast": pj.get("forecast"), "hourly": pj.get("forecastHourly"),
               "cors_points": p.headers.get("Access-Control-Allow-Origin"), "stations": []}
        for f in st:
            sid = f["properties"]["stationIdentifier"]; c = f["geometry"]["coordinates"]
            try:
                o = requests.get(f"https://api.weather.gov/stations/{sid}/observations/latest", headers=H, timeout=30).json()["properties"]
                obs = {"t": o.get("timestamp"), "temp_c": (o.get("temperature") or {}).get("value"), "text": o.get("textDescription"),
                       "pressure": (o.get("barometricPressure") or {}).get("value"), "wind": (o.get("windSpeed") or {}).get("value")}
            except Exception as e:
                obs = {"err": str(e)[:100]}
            res["stations"].append({"id": sid, "name": f["properties"]["name"], "km": round(dist((lat, lon), (c[1], c[0])), 1),
                                    "elev_m": (f["properties"].get("elevation") or {}).get("value"), "obs": obs})
        return res
    step("nws_" + k, nws)
    def acis(lat=lat, lon=lon):
        r = requests.post("https://data.rcc-acis.org/StnMeta", json={"bbox": [lon-0.35, lat-0.3, lon+0.35, lat+0.3], "elems": "maxt,mint,pcpn", "meta": "name,sids,valid_daterange,ll,elev"}, timeout=60)
        st = []
        for m in r.json().get("meta", []):
            vr = m.get("valid_daterange") or [[]]
            span = vr[0] if vr and vr[0] else []
            if span:
                st.append({"name": m["name"], "sids": m["sids"][:3], "range": span, "ll": m.get("ll"), "elev": m.get("elev")})
        st.sort(key=lambda s: s["range"][0])
        return {"cors": r.headers.get("Access-Control-Allow-Origin"), "stations": st[:10]}
    step("acis_" + k, acis)
def om():
    r = requests.get("https://api.open-meteo.com/v1/forecast?latitude=47.17&longitude=-122.52&current=temperature_2m&timezone=America/Los_Angeles", timeout=30)
    a = requests.get("https://archive-api.open-meteo.com/v1/archive?latitude=47.17&longitude=-122.52&start_date=1991-01-01&end_date=1991-01-03&daily=temperature_2m_max", timeout=30)
    return {"cors": r.headers.get("Access-Control-Allow-Origin"), "current": r.json().get("current"), "archive_ok": a.status_code, "archive": a.json().get("daily")}
step("openmeteo", om)
def acis_records():
    # daily records and normals for one well-known station (Reno airport) for today's date
    r = requests.post("https://data.rcc-acis.org/StnData", json={"sid": "RNOthr 9", "sdate": "por", "edate": "por", "elems": [{"name": "maxt", "interval": "dly", "duration": "dly", "smry": {"reduce": "max", "add": "date"}, "smry_only": 1, "groupby": "year"}]}, timeout=60)
    return {"status": r.status_code, "text": r.text[:600]}
step("acis_records_try", acis_records)
json.dump(out, open("tools/probe_out.json", "w"), indent=1, default=str)
