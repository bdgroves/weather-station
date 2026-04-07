# 🌡️ Weather Station

A high-end weather station dashboard for GitHub Pages, powered by [Open-Meteo](https://open-meteo.com/) and automated with GitHub Actions.

**Live:** [bdgroves.github.io/weather-station](https://bdgroves.github.io/weather-station)

## Stations

| Location | Elevation |
|----------|-----------|
| Lakewood, WA | 300 ft |
| Groveland, CA | 2,844 ft |
| Reno, NV | 4,505 ft |
| Death Valley, CA | -282 ft |

## Data

- **Current conditions** — temp, feels like, humidity, dew point, wind, pressure, visibility, cloud cover, precipitation
- **Air quality** — US AQI, PM2.5, PM10, ozone
- **48-hour hourly forecast** — temp, precip probability, wind, UV, weather conditions
- **7-day daily forecast** — hi/lo, precip, wind, UV, sunrise/sunset
- **24-hour trend charts** — temperature and barometric pressure

## Architecture

GitHub Actions cron → `fetch_weather.py` (stdlib only, no deps) → `data/weather.json` → static HTML/CSS/JS frontend

Updates every 30 minutes.

## Local Development

```bash
pixi run fetch
# then open index.html
```

## Credits

- Weather data: [Open-Meteo API](https://open-meteo.com/)
- Fonts: Barlow Condensed, IBM Plex Sans, JetBrains Mono
- Part of [brooksgroves.com](https://brooksgroves.com)
