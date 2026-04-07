#!/usr/bin/env python3
"""
Weather Station — fetch_weather.py
Fetches comprehensive weather data from Open-Meteo API for four locations.
Writes static JSON consumed by the frontend dashboard.
Python 3.12 stdlib only — no dependencies.
"""

import json
import urllib.request
import datetime
import os

LOCATIONS = [
    {"name": "Lakewood", "state": "WA", "lat": 47.1718, "lon": -122.5185, "tz": "America/Los_Angeles", "elevation_ft": 300},
    {"name": "Groveland", "state": "CA", "lat": 37.8463, "lon": -120.2313, "tz": "America/Los_Angeles", "elevation_ft": 2844},
    {"name": "Reno", "state": "NV", "lat": 39.5296, "lon": -119.8138, "tz": "America/Los_Angeles", "elevation_ft": 4505},
    {"name": "Death Valley", "state": "CA", "lat": 36.4620, "lon": -116.8666, "tz": "America/Los_Angeles", "elevation_ft": -282},
]

# WMO Weather interpretation codes
WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌦️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Slight showers", "🌦️"),
    81: ("Moderate showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm w/ slight hail", "⛈️"),
    99: ("Thunderstorm w/ heavy hail", "⛈️"),
}


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "WeatherStation/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def compass_direction(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = round(deg / 22.5) % 16
    return dirs[ix]


def fetch_location(loc):
    # Current weather + hourly (48h) + daily (7 days)
    current_params = ",".join([
        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
        "is_day", "precipitation", "rain", "showers", "snowfall",
        "weather_code", "cloud_cover", "pressure_msl", "surface_pressure",
        "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
        "dew_point_2m", "visibility",
    ])
    hourly_params = ",".join([
        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
        "precipitation_probability", "precipitation", "weather_code",
        "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
        "uv_index", "visibility", "cloud_cover", "dew_point_2m",
        "pressure_msl",
    ])
    daily_params = ",".join([
        "weather_code", "temperature_2m_max", "temperature_2m_min",
        "apparent_temperature_max", "apparent_temperature_min",
        "sunrise", "sunset", "daylight_duration",
        "uv_index_max", "precipitation_sum", "precipitation_probability_max",
        "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant",
    ])

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&current={current_params}"
        f"&hourly={hourly_params}"
        f"&daily={daily_params}"
        f"&temperature_unit=fahrenheit"
        f"&wind_speed_unit=mph"
        f"&precipitation_unit=inch"
        f"&timezone={loc['tz']}"
        f"&forecast_days=7"
    )

    data = fetch_json(url)

    # Air quality (separate endpoint)
    aqi_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?"
        f"latitude={loc['lat']}&longitude={loc['lon']}"
        f"&current=us_aqi,pm2_5,pm10,carbon_monoxide,ozone"
        f"&timezone={loc['tz']}"
    )
    try:
        aqi_data = fetch_json(aqi_url)
        aqi_current = aqi_data.get("current", {})
    except Exception:
        aqi_current = {}

    current = data.get("current", {})
    hourly = data.get("hourly", {})
    daily = data.get("daily", {})

    wmo = current.get("weather_code", 0)
    desc, icon = WMO_CODES.get(wmo, ("Unknown", "❓"))
    wind_dir = current.get("wind_direction_10m", 0)

    # Build 48-hour hourly array
    hourly_out = []
    times = hourly.get("time", [])
    for i in range(min(48, len(times))):
        h_wmo = hourly["weather_code"][i] if hourly.get("weather_code") and i < len(hourly["weather_code"]) else 0
        h_desc, h_icon = WMO_CODES.get(h_wmo, ("Unknown", "❓"))
        hourly_out.append({
            "time": times[i],
            "temp": hourly["temperature_2m"][i] if hourly.get("temperature_2m") else None,
            "feels_like": hourly["apparent_temperature"][i] if hourly.get("apparent_temperature") else None,
            "humidity": hourly["relative_humidity_2m"][i] if hourly.get("relative_humidity_2m") else None,
            "precip_prob": hourly["precipitation_probability"][i] if hourly.get("precipitation_probability") else None,
            "precip": hourly["precipitation"][i] if hourly.get("precipitation") else None,
            "weather_code": h_wmo,
            "weather_desc": h_desc,
            "weather_icon": h_icon,
            "wind_speed": hourly["wind_speed_10m"][i] if hourly.get("wind_speed_10m") else None,
            "wind_dir": hourly["wind_direction_10m"][i] if hourly.get("wind_direction_10m") else None,
            "wind_gusts": hourly["wind_gusts_10m"][i] if hourly.get("wind_gusts_10m") else None,
            "uv_index": hourly["uv_index"][i] if hourly.get("uv_index") else None,
            "visibility": hourly["visibility"][i] if hourly.get("visibility") else None,
            "cloud_cover": hourly["cloud_cover"][i] if hourly.get("cloud_cover") else None,
            "dew_point": hourly["dew_point_2m"][i] if hourly.get("dew_point_2m") else None,
            "pressure": hourly["pressure_msl"][i] if hourly.get("pressure_msl") else None,
        })

    # Build 7-day daily array
    daily_out = []
    d_times = daily.get("time", [])
    for i in range(min(7, len(d_times))):
        d_wmo = daily["weather_code"][i] if daily.get("weather_code") else 0
        d_desc, d_icon = WMO_CODES.get(d_wmo, ("Unknown", "❓"))
        daily_out.append({
            "date": d_times[i],
            "weather_code": d_wmo,
            "weather_desc": d_desc,
            "weather_icon": d_icon,
            "temp_max": daily["temperature_2m_max"][i] if daily.get("temperature_2m_max") else None,
            "temp_min": daily["temperature_2m_min"][i] if daily.get("temperature_2m_min") else None,
            "feels_max": daily["apparent_temperature_max"][i] if daily.get("apparent_temperature_max") else None,
            "feels_min": daily["apparent_temperature_min"][i] if daily.get("apparent_temperature_min") else None,
            "sunrise": daily["sunrise"][i] if daily.get("sunrise") else None,
            "sunset": daily["sunset"][i] if daily.get("sunset") else None,
            "daylight_hrs": round(daily["daylight_duration"][i] / 3600, 1) if daily.get("daylight_duration") and daily["daylight_duration"][i] else None,
            "uv_max": daily["uv_index_max"][i] if daily.get("uv_index_max") else None,
            "precip_sum": daily["precipitation_sum"][i] if daily.get("precipitation_sum") else None,
            "precip_prob_max": daily["precipitation_probability_max"][i] if daily.get("precipitation_probability_max") else None,
            "wind_max": daily["wind_speed_10m_max"][i] if daily.get("wind_speed_10m_max") else None,
            "wind_gusts_max": daily["wind_gusts_10m_max"][i] if daily.get("wind_gusts_10m_max") else None,
            "wind_dir_dominant": daily["wind_direction_10m_dominant"][i] if daily.get("wind_direction_10m_dominant") else None,
        })

    return {
        "location": {
            "name": loc["name"],
            "state": loc["state"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "elevation_ft": loc["elevation_ft"],
        },
        "current": {
            "temp": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "dew_point": current.get("dew_point_2m"),
            "weather_code": wmo,
            "weather_desc": desc,
            "weather_icon": icon,
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
        "air_quality": {
            "us_aqi": aqi_current.get("us_aqi"),
            "pm2_5": aqi_current.get("pm2_5"),
            "pm10": aqi_current.get("pm10"),
            "co": aqi_current.get("carbon_monoxide"),
            "ozone": aqi_current.get("ozone"),
        },
        "hourly": hourly_out,
        "daily": daily_out,
    }


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    all_data = {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

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

    output = {
        "generated_utc": now,
        "stations": all_data,
    }

    outpath = os.path.join(out_dir, "weather.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {outpath} ({os.path.getsize(outpath):,} bytes)")


if __name__ == "__main__":
    main()
