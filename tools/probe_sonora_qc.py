"""Probe: Sonora co-op lows in mid-September vs nearby stations (Columbia airport O22, Green Spring RAWS, other co-ops)."""
import json, requests
out = {}
for name, st, net in [("columbia_O22", "O22", "CA_ASOS")]:
    try:
        r = requests.get("https://mesonet.agron.iastate.edu/api/1/daily.json", params={"station": st, "network": net, "year": 2026, "month": 9}, timeout=60).json()
        out[name] = [[d["date"][5:], d.get("max_tmpf"), d.get("min_tmpf")] for d in r.get("data", []) if "09-10" <= d["date"][5:] <= "09-25"]
    except Exception as e:
        out[name] = str(e)[:200]
# ACIS: all stations within ~25 mi of Sonora with data for those dates
r = requests.get("https://data.rcc-acis.org/MultiStnData", params={"bbox": "-120.75,37.7,-120.0,38.25", "sdate": "2026-09-14", "edate": "2026-09-24", "elems": "mint", "meta": "name,elev,sids"}, timeout=90).json()
out["acis_neighbors"] = [[s["meta"]["name"], s["meta"].get("elev"), [v[0] if isinstance(v, list) else v for v in s["data"]]] for s in r.get("data", []) if any((v[0] if isinstance(v, list) else v) not in ("M", "") for v in s["data"])]
json.dump(out, open("tools/probe_out.json", "w"), indent=0)
