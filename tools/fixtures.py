"""Record real responses from every live endpoint the page calls, for offline UI testing."""
import json, urllib.request, urllib.parse
UA = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Accept": "application/geo+json"}
S = [("KTCM", 47.1718, -122.5185, "SEW", 115, 49), ("MOUC1", 37.8463, -120.2313, "STO", 79, 27),
     ("KRNO", 39.5296, -119.8138, "REV", 45, 106), ("DEVC1", 36.4620, -116.8666, "VEF", 63, 120)]
urls = []
for sid, lat, lon, off, x, y in S:
    urls += [f"https://api.weather.gov/stations/{sid}/observations/latest",
             f"https://api.weather.gov/stations/{sid}/observations?limit=200",
             f"https://api.weather.gov/alerts/active?point={lat},{lon}",
             f"https://api.weather.gov/gridpoints/{off}/{x},{y}/forecast",
             f"https://api.weather.gov/products/types/AFD/locations/{off}"]
out = {}
for u in urls:
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
            out[u] = r.read().decode()
        if "/products/types/AFD/" in u:
            first = json.loads(out[u])["@graph"][0]["@id"]
            with urllib.request.urlopen(urllib.request.Request(first, headers=UA), timeout=60) as r:
                out[first] = r.read().decode()
    except Exception as e:
        out[u] = json.dumps({"fixture_error": str(e)})
json.dump(out, open("tools/probe_out.json", "w"))
print(len(out), "responses")
