"""Probe: Iowa Environmental Mesonet as a fallback for NWS observations and forecast discussions."""
import json, requests
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Origin": "https://brooksgroves.com"}
out = {}
def t(name, url, n=600):
    try:
        r = requests.get(url, headers=H, timeout=40)
        out[name] = {"status": r.status_code, "cors": r.headers.get("Access-Control-Allow-Origin"), "type": r.headers.get("Content-Type"), "body": r.text[:n]}
    except Exception as e:
        out[name] = {"err": str(e)[:200]}
t("currents_station", "https://mesonet.agron.iastate.edu/api/1/currents.json?station=KLAW", 1500)
t("currents_network", "https://mesonet.agron.iastate.edu/api/1/currents.json?network=OK_ASOS", 400)
t("obhistory", "https://mesonet.agron.iastate.edu/api/1/obhistory.json?station=LAW&network=OK_ASOS", 1200)
t("network_geojson", "https://mesonet.agron.iastate.edu/geojson/network/OK_ASOS.geojson", 800)
t("afos_retrieve", "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=AFDOUN&limit=1&fmt=text", 800)
t("nwstext_list", "https://mesonet.agron.iastate.edu/api/1/nws/afos/list.json?pil=AFDOUN", 600)
t("asos_csv", "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=LAW&data=tmpf&data=dwpf&data=relh&data=sknt&data=drct&data=gust&data=mslp&data=alti&data=vsby&data=skyc1&data=skyl1&tz=Etc/UTC&format=onlycomma&latlon=no&missing=empty&trace=empty&hours=6", 800)
t("nws_points", "https://api.weather.gov/points/34.609,-98.39", 300)
json.dump(out, open("tools/probe_out.json", "w"), indent=1)
