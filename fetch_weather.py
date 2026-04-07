#!/usr/bin/env python3
"""
Weather Station — fetch_weather.py
Fetches comprehensive weather data from Open-Meteo API for four locations.
Fetches NWS active alerts for each location.
Calculates moon phase and illumination.
Writes static JSON consumed by the frontend dashboard.
Python 3.12 stdlib only — no dependencies.
"""

import json
import urllib.request
import datetime
import math
import os

LOCATIONS = [
    {"name": "Lakewood", "state": "WA", "lat": 47.1718, "lon": -122.5185, "tz": "America/Los_Angeles", "elevation_ft": 300},
    {"name": "Groveland", "state": "CA", "lat": 37.8463, "lon": -120.2313, "tz": "America/Los_Angeles", "elevation_ft": 2844},
    {"name": "Reno", "state": "NV", "lat": 39.5296, "lon": -119.8138, "tz": "America/Los_Angeles", "elevation_ft": 4505},
    {"name": "Death Valley", "state": "CA", "lat": 36.4620, "lon": -116.8666, "tz": "America/Los_Angeles", "elevation_ft": -282},
]

WMO_CODES = {
    0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"), 45: ("Fog", "🌫️"), 48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"), 53: ("Moderate drizzle", "🌦️"), 55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"), 57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌦️"), 63: ("Moderate rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"), 67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow", "🌨️"), 73: ("Moderate snow", "🌨️"), 75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"), 80: ("Slight showers", "🌦️"), 81: ("Moderate showers", "🌧️"),
    82: ("Violent showers", "⛈️"), 85: ("Slight snow showers", "🌨️"), 86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm w/ slight hail", "⛈️"),
    99: ("Thunderstorm w/ heavy hail", "⛈️"),
}


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "WeatherStation/1.0 (github.com/bdgroves/weather-station)",
        "Accept": "application/geo+json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def compass_direction(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / 22.5) % 16]


def moon_phase():
    """Moon phase via Julian day calculation."""
    now = datetime.datetime.now(datetime.timezone.utc)
    y, m, d = now.year, now.month, now.day
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + A // 4
    JD = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
    synodic = 29.53058867
    age = (JD - 2451550.1) % synodic
    illumination = (1 - math.cos(2 * math.pi * age / synodic)) / 2 * 100

    phases = [
        (1.85, "New Moon", "🌑"), (5.53, "Waxing Crescent", "🌒"),
        (9.22, "First Quarter", "🌓"), (12.91, "Waxing Gibbous", "🌔"),
        (16.61, "Full Moon", "🌕"), (20.30, "Waning Gibbous", "🌖"),
        (23.99, "Last Quarter", "🌗"), (27.68, "Waning Crescent", "🌘"),
    ]
    name, emoji = "New Moon", "🌑"
    for threshold, n, e in phases:
        if age < threshold:
            name, emoji = n, e
            break

    full_age = synodic / 2
    days_to_full = (full_age - age) if age < full_age else (synodic - age + full_age)

    return {
        "phase_name": name, "emoji": emoji,
        "illumination": round(illumination, 1),
        "age_days": round(age, 1),
        "days_to_full": round(days_to_full, 1),
        "days_to_new": round(synodic - age, 1),
    }


def fetch_nws_alerts(lat, lon):
    """Fetch active NWS alerts for a point."""
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}&status=actual"
    try:
        data = fetch_json(url)
        alerts = []
        for feat in data.get("features", []):
            p = feat.get("properties", {})
            sev = p.get("severity", "Unknown")
            color = {"Extreme": "red", "Severe": "orange", "Moderate": "yellow"}.get(sev, "blue")
            alerts.append({
                "event": p.get("event", "Unknown"),
                "severity": sev,
                "urgency": p.get("urgency", ""),
                "headline": p.get("headline", ""),
                "description": (p.get("description") or "")[:500],
                "instruction": (p.get("instruction") or "")[:300],
                "onset": p.get("onset", ""),
                "expires": p.get("expires", ""),
                "sender": p.get("senderName", ""),
                "color": color,
            })
        return alerts
    except Exception as e:
        print(f"    NWS alerts error: {e}")
        return []


def calc_pressure_trend(hourly):
    """3-hour pressure trend from hourly data."""
    p = hourly.get("pressure_msl", [])
    times = hourly.get("time", [])
    if not p or len(p) < 4:
        return {"direction": "steady", "change_3h": 0, "arrow": "→"}

    now_h = datetime.datetime.now().hour
    idx = min(now_h, len(p) - 1)
    idx3 = max(0, idx - 3)

    if p[idx] is None or p[idx3] is None:
        return {"direction": "steady", "change_3h": 0, "arrow": "→"}

    change = round(p[idx] - p[idx3], 1)
    if change > 1.5:
        return {"direction": "rising_fast", "change_3h": change, "arrow": "⬆"}
    elif change > 0.5:
        return {"direction": "rising", "change_3h": change, "arrow": "↗"}
    elif change < -1.5:
        return {"direction": "falling_fast", "change_3h": change, "arrow": "⬇"}
    elif change < -0.5:
        return {"direction": "falling", "change_3h": change, "arrow": "↘"}
    return {"direction": "steady", "change_3h": change, "arrow": "→"}


def fetch_location(loc):
    current_params = ",".join([
        "temperature_2m","relative_humidity_2m","apparent_temperature",
        "is_day","precipitation","rain","showers","snowfall",
        "weather_code","cloud_cover","pressure_msl","surface_pressure",
        "wind_speed_10m","wind_direction_10m","wind_gusts_10m",
        "dew_point_2m","visibility",
    ])
    hourly_params = ",".join([
        "temperature_2m","relative_humidity_2m","apparent_temperature",
        "precipitation_probability","precipitation","weather_code",
        "wind_speed_10m","wind_direction_10m","wind_gusts_10m",
        "uv_index","visibility","cloud_cover","dew_point_2m","pressure_msl",
    ])
    daily_params = ",".join([
        "weather_code","temperature_2m_max","temperature_2m_min",
        "apparent_temperature_max","apparent_temperature_min",
        "sunrise","sunset","daylight_duration",
        "uv_index_max","precipitation_sum","precipitation_probability_max",
        "wind_speed_10m_max","wind_gusts_10m_max","wind_direction_10m_dominant",
    ])

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&current={current_params}&hourly={hourly_params}&daily={daily_params}"
        f"&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
        f"&timezone={loc['tz']}&forecast_days=7"
    )
    data = fetch_json(url)

    aqi_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&current=us_aqi,pm2_5,pm10,carbon_monoxide,ozone&timezone={loc['tz']}"
    )
    try:
        aqi_current = fetch_json(aqi_url).get("current", {})
    except Exception:
        aqi_current = {}

    current = data.get("current", {})
    hourly = data.get("hourly", {})
    daily = data.get("daily", {})
    wmo = current.get("weather_code", 0)
    desc, icon = WMO_CODES.get(wmo, ("Unknown", "❓"))
    wind_dir = current.get("wind_direction_10m", 0)

    pressure_trend = calc_pressure_trend(hourly)

    print(f"  Fetching NWS alerts...")
    alerts = fetch_nws_alerts(loc["lat"], loc["lon"])
    if alerts:
        print(f"  ⚠ {len(alerts)} alert(s): {', '.join(a['event'] for a in alerts)}")
    else:
        print(f"  ✓ No active alerts")

    # Build hourly
    hourly_out = []
    times = hourly.get("time", [])
    for i in range(min(48, len(times))):
        h_wmo = (hourly.get("weather_code") or [])[i] if i < len(hourly.get("weather_code", [])) else 0
        h_desc, h_icon = WMO_CODES.get(h_wmo, ("Unknown", "❓"))
        hourly_out.append({
            "time": times[i],
            "temp": (hourly.get("temperature_2m") or [None]*48)[i],
            "feels_like": (hourly.get("apparent_temperature") or [None]*48)[i],
            "humidity": (hourly.get("relative_humidity_2m") or [None]*48)[i],
            "precip_prob": (hourly.get("precipitation_probability") or [None]*48)[i],
            "precip": (hourly.get("precipitation") or [None]*48)[i],
            "weather_code": h_wmo, "weather_desc": h_desc, "weather_icon": h_icon,
            "wind_speed": (hourly.get("wind_speed_10m") or [None]*48)[i],
            "wind_dir": (hourly.get("wind_direction_10m") or [None]*48)[i],
            "wind_gusts": (hourly.get("wind_gusts_10m") or [None]*48)[i],
            "uv_index": (hourly.get("uv_index") or [None]*48)[i],
            "visibility": (hourly.get("visibility") or [None]*48)[i],
            "cloud_cover": (hourly.get("cloud_cover") or [None]*48)[i],
            "dew_point": (hourly.get("dew_point_2m") or [None]*48)[i],
            "pressure": (hourly.get("pressure_msl") or [None]*48)[i],
        })

    # Build daily
    daily_out = []
    d_times = daily.get("time", [])
    for i in range(min(7, len(d_times))):
        d_wmo = (daily.get("weather_code") or [0]*7)[i]
        d_desc, d_icon = WMO_CODES.get(d_wmo, ("Unknown", "❓"))
        daily_out.append({
            "date": d_times[i],
            "weather_code": d_wmo, "weather_desc": d_desc, "weather_icon": d_icon,
            "temp_max": (daily.get("temperature_2m_max") or [None]*7)[i],
            "temp_min": (daily.get("temperature_2m_min") or [None]*7)[i],
            "feels_max": (daily.get("apparent_temperature_max") or [None]*7)[i],
            "feels_min": (daily.get("apparent_temperature_min") or [None]*7)[i],
            "sunrise": (daily.get("sunrise") or [None]*7)[i],
            "sunset": (daily.get("sunset") or [None]*7)[i],
            "daylight_hrs": round(daily["daylight_duration"][i] / 3600, 1) if daily.get("daylight_duration") and daily["daylight_duration"][i] else None,
            "uv_max": (daily.get("uv_index_max") or [None]*7)[i],
            "precip_sum": (daily.get("precipitation_sum") or [None]*7)[i],
            "precip_prob_max": (daily.get("precipitation_probability_max") or [None]*7)[i],
            "wind_max": (daily.get("wind_speed_10m_max") or [None]*7)[i],
            "wind_gusts_max": (daily.get("wind_gusts_10m_max") or [None]*7)[i],
            "wind_dir_dominant": (daily.get("wind_direction_10m_dominant") or [None]*7)[i],
        })

    return {
        "location": {
            "name": loc["name"], "state": loc["state"],
            "lat": loc["lat"], "lon": loc["lon"],
            "elevation_ft": loc["elevation_ft"],
        },
        "current": {
            "temp": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "dew_point": current.get("dew_point_2m"),
            "weather_code": wmo, "weather_desc": desc, "weather_icon": icon,
            "is_day": current.get("is_day"),
            "cloud_cover": current.get("cloud_cover"),
            "pressure_msl": current.get("pressure_msl"),
            "surface_pressure": current.get("surface_pressure"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_dir_deg": wind_dir,
            "wind_dir": compass_direction(wind_dir) if wind_dir is not None else None,
            "wind_gusts": current.get("wind_gusts_10m"),
            "visibility": current.get("visibility"),
            "precipitation": current.get("precipitation"),
            "rain": current.get("rain"),
            "snowfall": current.get("snowfall"),
        },
        "pressure_trend": pressure_trend,
        "air_quality": {
            "us_aqi": aqi_current.get("us_aqi"),
            "pm2_5": aqi_current.get("pm2_5"),
            "pm10": aqi_current.get("pm10"),
            "co": aqi_current.get("carbon_monoxide"),
            "ozone": aqi_current.get("ozone"),
        },
        "alerts": alerts,
        "hourly": hourly_out,
        "daily": daily_out,
    }


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    all_data = {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    moon = moon_phase()
    print(f"Moon: {moon['emoji']} {moon['phase_name']} — {moon['illumination']}% illuminated")

    for loc in LOCATIONS:
        key = f"{loc['name'].lower().replace(' ', '_')}_{loc['state'].lower()}"
        print(f"Fetching {loc['name']}, {loc['state']}...")
        try:
            result = fetch_location(loc)
            all_data[key] = result
            print(f"  ✓ {result['current']['temp']}°F, {result['current']['weather_desc']}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_data[key] = {"error": str(e), "location": {"name": loc["name"], "state": loc["state"]}}

    output = {"generated_utc": now, "moon": moon, "stations": all_data}
    outpath = os.path.join(out_dir, "weather.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {outpath} ({os.path.getsize(outpath):,} bytes)")


if __name__ == "__main__":
    main()
