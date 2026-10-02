"""Probe: radar tile sources (IEM NEXRAD composite TMS with time offsets; RainViewer)."""
import json, requests
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Origin": "https://brooksgroves.com", "Referer": "https://brooksgroves.com/weather-station/"}
out = {}
for name, url in [
    ("iem_now", "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913/7/20/44.png"),
    ("iem_m05", "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913-m05m/7/20/44.png"),
    ("iem_m50", "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913-m50m/7/20/44.png"),
    ("iem_json", "https://mesonet.agron.iastate.edu/data/gis/images/4326/USCOMP/n0q_0.json"),
    ("rainviewer", "https://api.rainviewer.com/public/weather-maps.json"),
    ("carto", "https://a.basemaps.cartocdn.com/dark_all/7/20/44.png"),
]:
    try:
        r = requests.get(url, headers=H, timeout=40)
        out[name] = {"status": r.status_code, "type": r.headers.get("Content-Type"), "len": len(r.content), "cors": r.headers.get("Access-Control-Allow-Origin"),
                     "body": r.text[:500] if "json" in (r.headers.get("Content-Type") or "") else None}
    except Exception as e:
        out[name] = str(e)[:200]
json.dump(out, open("tools/probe_out.json", "w"), indent=1)
