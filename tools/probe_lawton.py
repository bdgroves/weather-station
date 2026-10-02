"""Probe: Lawton September 2026 daily highs/lows from ACIS (airport and threaded) vs IEM's daily summary."""
import json, requests
out = {}
for name, q in [("muni_uid", {"uid": "13855"}), ("lawthr", {"sid": "LAWthr 9"}), ("muni_sid", {"sid": "03950 1"})]:
    try:
        r = requests.get("https://data.rcc-acis.org/StnData", params={**q, "sdate": "2026-09-01", "edate": "2026-10-02", "elems": "maxt,mint,pcpn", "meta": "name,sids"}, timeout=60).json()
        out[name] = {"meta": r.get("meta"), "data": r.get("data", [])[:40]}
    except Exception as e:
        out[name] = str(e)
try:
    r = requests.get("https://mesonet.agron.iastate.edu/api/1/daily.json", params={"station": "LAW", "network": "OK_ASOS", "year": 2026, "month": 9}, timeout=60).json()
    out["iem_daily"] = [[d.get("date"), d.get("max_tmpf"), d.get("min_tmpf"), d.get("precip")] for d in r.get("data", [])]
except Exception as e:
    out["iem_daily"] = str(e)
json.dump(out, open("tools/probe_out.json", "w"), indent=0)
