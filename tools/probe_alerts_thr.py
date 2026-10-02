"""Probe: IEM alert endpoints by point; ACIS threaded (ThreadEx) stations by FAA id."""
import json, requests, datetime as dt
H = {"User-Agent": "WeatherStation/2.0 (github.com/bdgroves/weather-station)", "Origin": "https://brooksgroves.com"}
out = {}
today = dt.date.today(); s = (today - dt.timedelta(days=10)).isoformat(); e = (today + dt.timedelta(days=1)).isoformat()
def t(name, url, params=None, n=900):
    try:
        r = requests.get(url, params=params, headers=H, timeout=60)
        out[name] = {"url": r.url, "status": r.status_code, "cors": r.headers.get("Access-Control-Allow-Origin"), "body": r.text[:n]}
    except Exception as ex:
        out[name] = {"err": str(ex)[:200]}
for lat, lon, tag in [(37.9841, -120.3822, "sonora")]:
    t(f"vtec_bypoint_{tag}", "https://mesonet.agron.iastate.edu/json/vtec_events_bypoint.py", {"lat": lat, "lon": lon, "sdate": s, "edate": e})
    t(f"api_vtec_bypoint_{tag}", "https://mesonet.agron.iastate.edu/api/1/vtec/events_bypoint.json", {"lat": lat, "lon": lon, "sdate": s, "edate": e})
    t(f"sbw_bypoint_{tag}", "https://mesonet.agron.iastate.edu/json/sbw_by_point.py", {"lat": lat, "lon": lon, "sdate": s, "edate": e})
    t(f"api_sbw_bypoint_{tag}", "https://mesonet.agron.iastate.edu/api/1/vtec/sbw_bypoint.json", {"lat": lat, "lon": lon, "sdate": s, "edate": e})
t("api_ugc_county", "https://mesonet.agron.iastate.edu/api/1/vtec/county_zone.geojson", None, 400)
t("api_events_active", "https://mesonet.agron.iastate.edu/api/1/vtec/events.json", {"wfo": "STO", "sdate": s, "edate": e}, 1500)
# ThreadEx: StnMeta by FAA-derived thread ids, and does a bbox listing include them?
t("thr_meta", "https://data.rcc-acis.org/StnMeta", {"sids": "LAWthr 9,SEAthr 9,RNOthr 9,BOIthr 9,CNYthr 9,BDNthr 9,RDMthr 9", "meta": "name,sids,ll,valid_daterange", "elems": "maxt"}, 2500)
t("bbox_thr", "https://data.rcc-acis.org/StnMeta", {"bbox": "-98.84,34.16,-97.94,35.06", "meta": "name,sids", "elems": "maxt", "network": "9"} , 800)
json.dump(out, open("tools/probe_out.json", "w"), indent=1)
