#!/usr/bin/env python3
"""
Weather Station — fetch_weather.py
───────────────────────────────────────────────────────────────────────────────
The page reads live data straight from the sources in the browser (NWS
observations, alerts and forecasts; Open-Meteo forecasts and air quality), so
it is never older than a few minutes. This script does the slow and heavy
work once an hour in GitHub Actions:

  data/weather.json   a snapshot of everything, used only if a live source
                      fails (and by anything else that wants one file)
  data/climate.json   for each station's long-record climate site (ACIS):
                      record high/low for every day of the year with the year
                      it happened, 1991–2020 normals, and this month and this
                      water year against normal. Rebuilt daily.

Observed vs modelled: "current conditions" used to be Open-Meteo's model
estimate for the grid square. They are now the latest real observation from
the nearest NWS station, and the model is shown beside it as a forecast.

Python 3.12 stdlib only.
"""

import datetime as dt
import json
import math
import os
import time
import urllib.request

UA = "WeatherStation/2.0 (github.com/bdgroves/weather-station)"
OUT = os.path.join(os.path.dirname(__file__), "data")

# obs: NWS observation stations, best first. climate: ACIS station with the long record.
STATIONS = [
    {"key": "lakewood_wa", "name": "Lakewood", "state": "WA", "lat": 47.1718, "lon": -122.5185, "elevation_ft": 300,
     "tz": "America/Los_Angeles", "nws": "SEW", "obs": ["KTCM", "KTIW", "KPLU"],
     "climate": {"sid": "SEAthr 9", "label": "Sea-Tac Airport"}},
    {"key": "groveland_ca", "name": "Groveland", "state": "CA", "lat": 37.8463, "lon": -120.2313, "elevation_ft": 2844,
     "tz": "America/Los_Angeles", "nws": "STO", "obs": ["MOUC1", "GNSC1"],
     "obs_note": "No official station near Groveland. The nearest is the Mount Elizabeth fire-weather station, 15 miles away and 2,100 ft higher.",
     "climate": {"sid": "048353 2", "label": "Sonora (1,675 ft), the nearest century-long record"}},
    {"key": "reno_nv", "name": "Reno", "state": "NV", "lat": 39.5296, "lon": -119.8138, "elevation_ft": 4505,
     "tz": "America/Los_Angeles", "nws": "REV", "obs": ["KRNO"],
     "climate": {"sid": "RNOthr 9", "label": "Reno (airport and earlier city records)"}},
    {"key": "death_valley_ca", "name": "Death Valley", "state": "CA", "lat": 36.4620, "lon": -116.8666, "elevation_ft": -190,
     "tz": "America/Los_Angeles", "nws": "VEF", "obs": ["DEVC1"],
     "climate": {"sid": "042319 2", "label": "Death Valley (Furnace Creek / Greenland Ranch)"}},
]

WMO = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
       61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
       71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Showers", 81: "Showers",
       82: "Violent showers", 85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorm",
       96: "Thunderstorm, hail", 99: "Thunderstorm, heavy hail"}


def get(url, data=None, accept="application/geo+json", retries=3):
    body = json.dumps(data).encode() if data is not None else None
    hdr = {"User-Agent": UA, "Accept": accept}
    if body:
        hdr["Content-Type"] = "application/json"
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=hdr), timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"    retry {url[:60]}… ({e})")
            time.sleep(4 * (i + 1))


# ── Observations (NWS) ───────────────────────────────────────────────────────
def c2f(c):
    return None if c is None else round(c * 9 / 5 + 32, 1)


def latest_obs(st):
    for sid in st["obs"]:
        try:
            p = get(f"https://api.weather.gov/stations/{sid}/observations/latest")["properties"]
            v = lambda k: (p.get(k) or {}).get("value")
            if v("temperature") is None and v("windSpeed") is None:
                continue
            return {"station": sid, "name": p.get("stationName"), "time": p.get("timestamp"),
                    "text": p.get("textDescription") or None, "temp": c2f(v("temperature")),
                    "dewpoint": c2f(v("dewpoint")), "humidity": round(v("relativeHumidity")) if v("relativeHumidity") is not None else None,
                    "wind_mph": round(v("windSpeed") / 1.609, 1) if v("windSpeed") is not None else None,
                    "gust_mph": round(v("windGust") / 1.609, 1) if v("windGust") is not None else None,
                    "wind_dir": v("windDirection"),
                    "pressure_hpa": round(v("barometricPressure") / 100, 1) if v("barometricPressure") else None,
                    "visibility_mi": round(v("visibility") / 1609.34, 1) if v("visibility") is not None else None,
                    "heat_index": c2f(v("heatIndex")), "wind_chill": c2f(v("windChill"))}
        except Exception as e:
            print(f"    obs {sid}: {e}")
    return None


# ── Forecast snapshot (Open-Meteo) — fallback for the page ───────────────────
def forecast(st):
    hourly = "temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl,relative_humidity_2m,uv_index"
    daily = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,sunrise,sunset,uv_index_max"
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={st['lat']}&longitude={st['lon']}"
           f"&current=temperature_2m,weather_code,wind_speed_10m,pressure_msl&hourly={hourly}&daily={daily}"
           f"&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone={st['tz']}"
           f"&forecast_days=7&past_hours=24")
    d = get(url, accept="application/json")
    d["current"]["weather_text"] = WMO.get(d["current"].get("weather_code"), "")
    return {"current": d["current"], "hourly": d["hourly"], "daily": d["daily"],
            "utc_offset_seconds": d.get("utc_offset_seconds")}


def alerts(st):
    try:
        feats = get(f"https://api.weather.gov/alerts/active?point={st['lat']},{st['lon']}&status=actual")["features"]
        return [{"event": f["properties"]["event"], "severity": f["properties"]["severity"],
                 "headline": f["properties"]["headline"], "expires": f["properties"]["expires"],
                 "description": (f["properties"].get("description") or "")[:1500]} for f in feats]
    except Exception as e:
        print(f"    alerts: {e}")
        return []


# ── Climate (ACIS) ───────────────────────────────────────────────────────────
def acis_val(v):
    """ACIS strings: '72', 'M' missing, 'T' trace, '0.42A' accumulated, 'S' subsequent."""
    if v in ("M", "S", "", None):
        return None
    if v == "T":
        return 0.0
    try:
        return float(v.rstrip("ASTa"))
    except ValueError:
        return None


def climate(st):
    sid = st["climate"]["sid"]
    today = dt.date.today()
    d = get("https://data.rcc-acis.org/StnData",
            {"sid": sid, "sdate": "por", "edate": today.isoformat(), "elems": "maxt,mint,pcpn,snow", "meta": "name,sids,ll,elev"},
            accept="application/json")
    rows = d.get("data", [])
    meta = d.get("meta", {})
    by_md = {}                                   # "MM-DD" → lists
    days = []
    for date, mx, mn, pc, sn in rows:
        md = date[5:]
        e = by_md.setdefault(md, {"hi": [], "lo": [], "pcpn": []})
        mx, mn, pc = acis_val(mx), acis_val(mn), acis_val(pc)
        y = int(date[:4])
        if mx is not None:
            e["hi"].append((mx, y))
        if mn is not None:
            e["lo"].append((mn, y))
        if pc is not None and 1991 <= y <= 2020:
            e["pcpn"].append(pc)
        days.append((date, mx, mn, pc, acis_val(sn)))

    keys = [f"{m:02d}-{dd:02d}" for m in range(1, 13) for dd in range(1, 32)
            if not (m in (4, 6, 9, 11) and dd == 31) and not (m == 2 and dd > 29)]

    def window(i, field, years=None):
        vals = []
        for k in range(i - 7, i + 8):
            for v, y in by_md.get(keys[k % len(keys)], {}).get(field, []):
                if years is None or years[0] <= y <= years[1]:
                    vals.append(v)
        return vals

    days_out = {}
    for i, k in enumerate(keys):
        e = by_md.get(k)
        if not e or not e["hi"]:
            continue
        nh, nl = window(i, "hi", (1991, 2020)), window(i, "lo", (1991, 2020))
        rh = max(e["hi"], key=lambda t: (t[0], t[1]))
        rl = min(e["lo"], key=lambda t: (t[0], -t[1])) if e["lo"] else (None, None)
        # mean daily precip, smoothed over ±7 days
        pv = [v for kk in range(i - 7, i + 8) for v in by_md.get(keys[kk % len(keys)], {}).get("pcpn", [])]
        days_out[k] = {"normal_hi": round(sum(nh) / len(nh), 1) if nh else None,
                       "normal_lo": round(sum(nl) / len(nl), 1) if nl else None,
                       "record_hi": rh[0], "record_hi_year": rh[1],
                       "record_lo": rl[0], "record_lo_year": rl[1],
                       "normal_pcpn": round(sum(pv) / len(pv), 3) if pv else None}

    # recent daily values: last 400 days, for month-to-date and water-year-to-date
    recent = [{"date": a, "hi": b, "lo": c, "pcpn": p, "snow": s} for a, b, c, p, s in days[-400:]]
    first_year = int(rows[0][0][:4]) if rows else None
    return {"sid": sid, "label": st["climate"]["label"], "name": meta.get("name"), "elev_ft": meta.get("elev"),
            "first_year": first_year, "last_date": rows[-1][0] if rows else None,
            "days": days_out, "recent": recent}


def moon():
    """Moon phase from the current instant (synodic month from a known new moon)."""
    now = dt.datetime.now(dt.timezone.utc)
    jd = now.timestamp() / 86400 + 2440587.5
    syn = 29.530588853
    age = (jd - 2451550.09766) % syn
    illum = (1 - math.cos(2 * math.pi * age / syn)) / 2
    names = ["New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", "Full Moon",
             "Waning Gibbous", "Last Quarter", "Waning Crescent"]
    return {"age_days": round(age, 2), "illumination": round(illum * 100, 1),
            "phase": names[int((age / syn) * 8 + 0.5) % 8],
            "days_to_full": round((syn / 2 - age) % syn, 1), "days_to_new": round(syn - age, 1)}


def main():
    os.makedirs(OUT, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    snap = {"generated_utc": now.isoformat(timespec="seconds"), "moon": moon(),
            "stations": {s["key"]: {k: s[k] for k in ("key", "name", "state", "lat", "lon", "elevation_ft", "tz", "nws", "obs")} | {"obs_note": s.get("obs_note")} for s in STATIONS}}
    ok = 0
    for st in STATIONS:
        print(f"{st['name']}, {st['state']}")
        rec = snap["stations"][st["key"]]
        try:
            rec["forecast"] = forecast(st)
            ok += 1
        except Exception as e:
            print(f"  forecast failed: {e}")
        rec["observed"] = latest_obs(st)
        try:
            rec["air_quality"] = get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={st['lat']}&longitude={st['lon']}"
                                     f"&current=us_aqi,pm2_5,pm10,ozone,us_aqi_pm2_5,us_aqi_ozone&hourly=us_aqi&timezone=auto&forecast_days=2",
                                     accept="application/json")
        except Exception as e:
            print(f"  air quality failed: {e}")
        rec["alerts"] = alerts(st)
        o = rec["observed"]
        print(f"  observed: {o and o['temp']}°F at {o and o['station']} ({o and o['time']}) · {len(rec['alerts'])} alerts")
    if not ok:
        print("::error::No forecasts fetched — keeping the published snapshot")
        raise SystemExit(1)
    with open(os.path.join(OUT, "weather.json"), "w") as f:
        json.dump(snap, f, separators=(",", ":"))

    # climate: once a day (ACIS updates overnight)
    cpath = os.path.join(OUT, "climate.json")
    old = json.load(open(cpath)) if os.path.exists(cpath) else {}
    if old.get("built") != now.date().isoformat():
        clim = {"built": now.date().isoformat(), "stations": {}}
        for st in STATIONS:
            try:
                c = climate(st)
                clim["stations"][st["key"]] = c
                print(f"  climate {st['name']}: {c['name']} since {c['first_year']}, through {c['last_date']}")
            except Exception as e:
                print(f"  climate {st['name']} failed: {e}")
                if st["key"] in old.get("stations", {}):
                    clim["stations"][st["key"]] = old["stations"][st["key"]]
        if clim["stations"]:
            with open(cpath, "w") as f:
                json.dump(clim, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
