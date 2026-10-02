# 🌪️ WEATHER STATION

### *"We got cows."*

**[🔴 LIVE DASHBOARD → brooksgroves.com/weather-station](https://brooksgroves.com/weather-station/)**

---

Look — I'm not made of money. A Davis Vantage Pro2 runs $700. A WeatherFlow Tempest? $330 and you still need wifi that works in your yard. You know what costs exactly zero dollars? A GitHub repo, a free weather API, and the unshakeable confidence that you can build something better with a Python script and some HTML.

This is that something.

**Weather Station** is a high-end, real-time weather dashboard that monitors four stations across the American West — from the soggy Pacific Northwest to the surface of the actual sun (Death Valley). It runs 24/7, reads live National Weather Service observations every 5 minutes, and looks like something you'd see bolted to a wall in a NOAA operations center. Except it's free. And it lives on GitHub Pages. And nobody had to drive into a tornado to get the data.

## 📡 THE STATIONS

Four locations. Four climates. One dashboard to rule them all.

| Station | Elev | The Vibe |
|---------|------|----------|
| **Lakewood, WA** | 300 ft | Home base. Pacific Northwest grey. The kind of place where "partly cloudy" is basically sunshine. |
| **Sonora, CA** | 1,785 ft | Tuolumne County seat, gold country, the road up to Yosemite. Home turf: I grew up just down the road in Groveland, chasing thunderstorms off the Sierra crest. |
| **Reno, NV** | 4,505 ft | High desert, big wind, bigger sky. Where a "partly sunny" forecast means the sun is fully trying to fight you. |
| **Death Valley, CA** | -190 ft | The hottest place on Earth. Below sea level. The station sits at Furnace Creek, 190 ft below sea level, where the record books start in 1911 — and where it hit 134°F on July 10, 1913. We monitor this one for sport. |

## 🛰️ WHAT'S ON THE DASHBOARD

This isn't your phone's weather app. This is the whole instrument panel — and now it's measured, not modelled.

| Station | Measured at | Records from |
|---|---|---|
| Lakewood | McChord AFB (KTCM), 2 mi | Sea-Tac Airport, since 1945 |
| Sonora | Green Spring RAWS (GNSC1), 12 mi, about 700 ft lower — there's no NWS station in town | Sonora, since 1903 |
| Reno | Reno–Tahoe airport (KRNO) | Reno, since 1893 |
| Death Valley | Furnace Creek visitor center (DEVC1) | Death Valley, since 1911 |

**Current conditions — measured.** The latest real observation from the nearest National Weather Service station, read live by the page every 5 minutes, with how old it is and where it came from. The model's value sits beside it as a check.

**Measured, then forecast.** One chart per variable: the solid line is what the station recorded over the last 24 hours, the dashed line is the forecast for the next 48, with the 1991–2020 normal band behind them. Pressure and wind on a second chart. *It's headed right for us.*

**Instruments** — wind compass (the arrow points where the wind is going), barometer with the real 3-hour trend from the station's own readings, humidity and dew point with a comfort label, cloud layers and their heights, rain, UV.

**NWS alerts** — live, color-coded by severity, click to read the bulletin. Tabs get a dot when a station has an alert.

**Next seven days** — model highs and lows with the normal for each date underneath and a flag when a forecast reaches the record, plus the National Weather Service's own wording.

**From the forecaster** — the synopsis from the local NWS office's Area Forecast Discussion: what the atmosphere is doing, in a meteorologist's own words.

**How good is the forecast?** — every day the model's highs and lows 1–7 days ahead are scored against what the station measured (Open-Meteo's archive of its own past forecasts goes back to March 2026), beside two guesses a forecast should beat: the normal for the date, and "same as N days before". The National Weather Service's forecast is saved daily and joins the scoring as it builds up. Each forecast day shows how far off it usually is.

**Radar, the last hour** — the NWS NEXRAD composite every five minutes from the Iowa Environmental Mesonet, looping over a dark Esri map centred on the selected place.

**First freeze** — from each station's full history: the typical first 32° night, the 8-in-10 range, earliest and latest, the chance of one by today, this season so far, and the last spring freeze. Searched places too.

**Against the record books** — the last 30 days of highs and lows against the normal range and the record high and low for every date (with the year), this month vs normal, and rain since October 1 against the water-year normal. The home stations' last 400 days get a neighbor check: a day that disagrees with every nearby station by more than 12° is set aside (Sonora's co-op thermometer logged a week of faulty lows in September 2026).

**Air quality, sun and moon** — US AQI and what's driving it, daylight and how fast it's changing, moon phase drawn to scale.

**Any US place** — type a town ("Bend", "Sonora, CA") or a ZIP, pick from the suggestions, and the page finds the nearest NWS stations, forecast office and forecast for it, with its own link. Searched places get record books too: the page finds the nearest current ACIS station with temperature and rain, uses NOAA's official threaded record when there is one nearby (Lawton since 1912, Boise since 1875) or otherwise joins in older stations from the same town (Moab since 1893), and builds normals and records in the browser.

**When the NWS can't be reached** from a visitor's browser, the page reads the same station reports, forecast discussions and active alerts from the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/) and says so beside the reading.

## ⚙️ HOW IT WORKS

```
Your browser, every 5 minutes                     GitHub Actions, hourly
  ├─ NWS: latest observation + last 30 h            fetch_weather.py (stdlib only)
  ├─ NWS: alerts, forecast, forecast discussion       ├─ data/weather.json  backup snapshot
  ├─ Open-Meteo: hourly + 7-day forecast, AQI         └─ data/climate.json  ACIS records + 1991–2020
  └─ data/climate.json (records & normals)                                  normals, rebuilt daily
```

Everything live is fetched by the page itself, so it's never older than a few minutes. If a source is down, the page falls back to the hourly backup copy and says so. The Action commits every 3 hours (or when the daily climate rebuild lands).

*Until October 2026 the page showed Open-Meteo's model estimate as "current conditions", from a snapshot that was often 4–7 hours old — GitHub was quietly skipping most of the every-30-minutes runs.*

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
| Records back to 1893 | No | Yes |
| Moon phase | No | Yes |
| Looks like a NOAA ops center | No | Yes |
| GitHub Actions minutes | N/A | Free tier |
| **Total** | **$385–$765** | **$0.00** |

The math is clear.

## 📡 DATA SOURCES

- **Observations, alerts, forecasts, forecast discussions** — [NWS API](https://www.weather.gov/documentation/services-web-api) (free, no key, taxpayer-funded)
- **Records and normals** — [ACIS](https://www.rcc-acis.org/) from NOAA's Regional Climate Centers
- **Radar** — NWS NEXRAD composite via the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/); base map © Esri, HERE, Garmin, OpenStreetMap
- **Backup for observations and forecast discussions** — [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/), Iowa State University
- **Hourly and 7-day forecasts, air quality** — [Open-Meteo](https://open-meteo.com/) (free, no key, open source)
- **Moon phase** — calculated in the browser

## 🎨 DESIGN

Dark instrument panel aesthetic. Barlow Condensed for the industrial gauge readouts, IBM Plex Sans for body text, JetBrains Mono for data values. Amber accent on charcoal. Built to look like you're monitoring the atmosphere from a bunker in Oklahoma.

---

*Part of [brooksgroves.com](https://brooksgroves.com)*

*"The suck zone. It's the point basically where the twister sucks you up."*
