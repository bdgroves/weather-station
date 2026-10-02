"""Probe: order and issuance times of recent AFDs per office."""
import json, requests
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)"}
out = {}
for o in ["SEW", "STO", "REV", "VEF"]:
    try:
        g = requests.get(f"https://api.weather.gov/products/types/AFD/locations/{o}", headers=H, timeout=60).json()["@graph"]
        out[o] = [[x.get("issuanceTime"), x.get("issuingOffice"), x.get("@id")[-36:]] for x in g[:6]]
    except Exception as e:
        out[o] = str(e)
json.dump(out, open("tools/probe_out.json", "w"), indent=1)
