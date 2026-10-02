"""Probe: NWS grid and nearby observation stations for Sonora, CA."""
import json, math, requests
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Accept": "application/geo+json"}
lat, lon = 37.9841, -120.3822
out = {}
p = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=H, timeout=30).json()["properties"]
out["grid"] = [p["gridId"], p["gridX"], p["gridY"], p.get("forecastZone"), p.get("county")]
fs = requests.get(p["observationStations"], headers=H, timeout=30).json()["features"][:10]
out["stations"] = []
for f in fs:
    sid = f["properties"]["stationIdentifier"]; c = f["geometry"]["coordinates"]
    km = 6371*2*math.asin(math.sqrt(math.sin(math.radians(c[1]-lat)/2)**2+math.cos(math.radians(lat))*math.cos(math.radians(c[1]))*math.sin(math.radians(c[0]-lon)/2)**2))
    try:
        o = requests.get(f"https://api.weather.gov/stations/{sid}/observations?limit=30", headers=H, timeout=30).json()["features"]
        ts = [x["properties"]["timestamp"][5:16] for x in o]
        t = [(x["properties"].get("temperature") or {}).get("value") for x in o]
        pr = sum(1 for x in o if (x["properties"].get("barometricPressure") or {}).get("value"))
        sky = sum(1 for x in o if x["properties"].get("cloudLayers"))
        obs = {"n": len(o), "first": ts[-1] if ts else None, "last": ts[0] if ts else None, "temps": t[:6], "with_pressure": pr, "with_sky": sky, "text": o[0]["properties"].get("textDescription") if o else None}
    except Exception as e:
        obs = {"err": str(e)[:100]}
    out["stations"].append({"id": sid, "name": f["properties"]["name"], "km": round(km, 1), "elev_m": (f["properties"].get("elevation") or {}).get("value"), "obs": obs})
json.dump(out, open("tools/probe_out.json", "w"), indent=1)
