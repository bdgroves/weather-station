# 🌪️ WEATHER STATION

### *"We got cows."*

**[🔴 LIVE DASHBOARD → bdgroves.github.io/weather-station](https://bdgroves.github.io/weather-station)**

---

Look — I'm not made of money. A Davis Vantage Pro2 runs $700. A WeatherFlow Tempest? $330 and you still need wifi that works in your yard. You know what costs exactly zero dollars? A GitHub repo, a free weather API, and the unshakeable confidence that you can build something better with a Python script and some HTML.

This is that something.

**Weather Station** is a high-end, real-time weather dashboard that monitors four stations across the American West — from the soggy Pacific Northwest to the surface of the actual sun (Death Valley). It runs 24/7, updates every 15 minutes, and looks like something you'd see bolted to a wall in a NOAA operations center. Except it's free. And it lives on GitHub Pages. And nobody had to drive into a tornado to get the data.

## 📡 THE STATIONS

Four locations. Four climates. One dashboard to rule them all.

| Station | Elev | The Vibe |
|---------|------|----------|
| **Lakewood, WA** | 300 ft | Home base. Pacific Northwest grey. The kind of place where "partly cloudy" is basically sunshine. |
| **Groveland, CA** | 2,844 ft | Gateway to Yosemite. Pine trees, gold country air, and the town where I grew up chasing thunderstorms off the Sierra crest. |
| **Reno, NV** | 4,505 ft | High desert, big wind, bigger sky. Where a "partly sunny" forecast means the sun is fully trying to fight you. |
| **Death Valley, CA** | -282 ft | The hottest place on Earth. Below sea level. The barometric pressure here is *higher* than sea level because you're in a geological hole. We monitor this one for sport. |

## 🛰️ WHAT'S ON THE DASHBOARD

This isn't your phone's weather app. This is the whole instrument panel.

**Current Conditions** — Temperature, feels like, humidity, dew point, cloud cover. The basics, but rendered like they belong on a broadcast.

**Wind Compass** — A proper SVG compass dial showing real-time wind direction with a rotated arrow. Not just "SW at 8 mph" — you can *see* where it's coming from. Bill Paxton would approve.

**Barometric Pressure + Trend Arrow** — The barometer reading plus a 3-hour trend indicator. Rising? Falling fast? Steady? The arrow tells you what's coming before the clouds do. This is how storm chasers read the sky.

**NWS Alerts** — Live alerts pulled straight from the National Weather Service. Heat advisories in Death Valley. Wind advisories in Reno. The occasional frost warning in Groveland. They show up as color-coded banners — red for extreme, orange for severe, yellow for moderate. Click to expand the full NWS bulletin. Tabs get a colored dot when a station has active alerts so you know something's brewing before you even click over.

**Astronomy Panel** — Moon phase, illumination percentage, age in days, and countdowns to the next full and new moon. Calculated via Julian day math, no API needed. Because weather people are also sky people.

**Air Quality** — US AQI, PM2.5, PM10, and ozone. Critical during wildfire season out west.

**48-Hour Hourly Forecast** — Scrollable strip with temp, precipitation probability, wind speed, and condition icons for every hour across two days.

**7-Day Forecast** — Daily cards with highs, lows, precipitation, wind, and UV index.

**Sun & Daylight** — Sunrise, sunset, daylight hours, and a progress bar showing where we are in the day.

**24-Hour Trend Charts** — Temperature and barometric pressure plotted on canvas-drawn charts with gradient fills. Watch the pressure drop. Feel the front coming in. *It's headed right for us.*

## ⚙️ HOW IT WORKS

Same architecture I use for everything — the GitHub Actions pattern:

```
GitHub Actions (cron every 15 min)
    → fetch_weather.py (Python 3.12, stdlib only, zero deps)
        → Open-Meteo API (weather + air quality)
        → NWS API (active alerts)
        → Moon phase (calculated, no API)
    → data/weather.json
        → index.html (static frontend, fetches JSON client-side)
            → Your eyeballs
```

No frameworks. No npm install. No node_modules black hole. Just Python that writes JSON and HTML that reads it. The way the founders intended.

## 🏃 RUN IT YOURSELF

```bash
pixi install
pixi run fetch
# open index.html
```

Or just look at the [live dashboard](https://bdgroves.github.io/weather-station) like a normal person.

## 💰 COST ANALYSIS

| Item | Weather Station (Physical) | This Project |
|------|---------------------------|--------------|
| Hardware | $330–$700 | $0 |
| Monthly fees | $0–$10 | $0 |
| Batteries | $15/year | $0 |
| Mounting pole | $40 | $0 |
| Crawling on roof | Required | Not required |
| Covers 4 locations simultaneously | No | Yes |
| NWS alerts | No | Yes |
| Moon phase | No | Yes |
| Looks like a NOAA ops center | No | Yes |
| GitHub Actions minutes | N/A | Free tier |
| **Total** | **$385–$765** | **$0.00** |

The math is clear.

## 📡 DATA SOURCES

- **Weather & Forecasts** — [Open-Meteo API](https://open-meteo.com/) (free, no key, open source)
- **Air Quality** — [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- **Alerts** — [NWS API](https://www.weather.gov/documentation/services-web-api) (free, no key, taxpayer-funded)
- **Moon Phase** — Calculated via Julian day method (been working since 45 BC, still going strong)

## 🎨 DESIGN

Dark instrument panel aesthetic. Barlow Condensed for the industrial gauge readouts, IBM Plex Sans for body text, JetBrains Mono for data values. Amber accent on charcoal. Built to look like you're monitoring the atmosphere from a bunker in Oklahoma.

---

*Part of [brooksgroves.com](https://brooksgroves.com)*

*"The suck zone. It's the point basically where the twister sucks you up."*
