# Feature catalogue

100 features, each with the file that implements it. Everything here is
reachable in demo mode, with no API key.

## Search and places

| # | Feature | Implementation |
|---|---|---|
| 1 | Type-ahead place search, prefix matches ranked first | `weatherapp/places.py`, `static/js/ui/search.js` |
| 2 | Suggestion list fully keyboard-driven (arrows, Enter, Escape) | `static/js/ui/search.js` |
| 3 | Coordinate queries such as `51.5,-0.12` | `weatherapp/providers/base.py` |
| 4 | Browser geolocation lookup | `static/js/main.js` |
| 5 | Saved places, persisted locally | `static/js/core/places.js` |
| 6 | Reorder saved places | `static/js/core/places.js` |
| 7 | A home place that loads on a bare visit | `static/js/core/places.js`, `main.js` |
| 8 | Recent-search history | `static/js/core/places.js` |
| 9 | Unknown place names still resolve to a stable location in demo mode | `weatherapp/providers/demo.py` |
| 10 | Side-by-side comparison of two places, with winners marked | `weatherapp/web/api.py`, `static/js/panels/tools.js` |
| 11 | Deep links (`?q=`) with working back/forward | `static/js/main.js` |
| 12 | Share sheet with clipboard fallback | `static/js/main.js` |

## Current conditions

| # | Feature | Implementation |
|---|---|---|
| 13 | Temperature readout with the condition named | `static/js/panels/core.js` |
| 14 | 19 hand-drawn line-art condition symbols | `static/js/draw/symbols.js` |
| 15 | Separate night symbol for clear skies | `static/js/draw/symbols.js` |
| 16 | "Feels like" that names which index it used | `weatherapp/meteorology/thermal.py` |
| 17 | NWS heat index (Rothfusz, both RH adjustments) | `weatherapp/meteorology/thermal.py` |
| 18 | NWS wind chill, correctly undefined outside its range | `weatherapp/meteorology/thermal.py` |
| 19 | Canadian humidex | `weatherapp/meteorology/thermal.py` |
| 20 | BOM apparent temperature | `weatherapp/meteorology/thermal.py` |
| 21 | Magnus dew point, and its inverse | `weatherapp/meteorology/thermal.py` |
| 22 | Three-hour barometric tendency with a plain-language reading | `weatherapp/meteorology/timeline.py` |
| 23 | Wind speed, gusts, and a squall note when the spread is wide | `static/js/panels/core.js` |
| 24 | 16-point cardinal direction | `weatherapp/meteorology/wind.py` |
| 25 | Beaufort force with its observable description | `weatherapp/meteorology/wind.py` |
| 26 | Cloud cover, visibility, precipitation, humidity | `static/js/panels/core.js` |
| 27 | Local time, time zone and UTC offset for the place, not the reader | `static/js/core/format.js` |
| 28 | Full reading log of every observed value | `static/js/panels/core.js` |

## Instruments

| # | Feature | Implementation |
|---|---|---|
| 29 | Barometer dial with graduated scale and needle | `static/js/draw/instruments.js` |
| 30 | Wind rose compass showing where the wind comes from | `static/js/draw/instruments.js` |
| 31 | Authentic wind barbs: pennant 50 kt, barb 10 kt, half 5 kt | `weatherapp/meteorology/wind.py`, `draw/instruments.js` |
| 32 | Synoptic station plot: sky cover, temperature, dew point, pressure code, barb | `static/js/draw/instruments.js` |
| 33 | Thermometer column showing now against today's range | `static/js/draw/instruments.js` |
| 34 | Comfort arc gauge | `static/js/draw/instruments.js` |
| 35 | UV ladder with banded risk colours | `static/js/draw/instruments.js` |
| 36 | Moon disc drawn with an SVG mask, correct through gibbous phases | `static/js/draw/instruments.js` |
| 37 | Live isobar background whose spacing follows the real pressure spread | `static/js/draw/isobars.js` |

## Forecast

| # | Feature | Implementation |
|---|---|---|
| 38 | 48-hour meteogram on ruled graph paper | `static/js/draw/charts.js` |
| 39 | Night shaded as bands behind the curves | `static/js/draw/charts.js` |
| 40 | Feels-like drawn as a dashed overlay | `static/js/draw/charts.js` |
| 41 | Precipitation bars on their own scale | `static/js/draw/charts.js` |
| 42 | Dashed leader-line callouts on the warmest and coldest hours | `static/js/draw/charts.js` |
| 43 | Sunrise and sunset gnomons marked on the chart | `static/js/draw/charts.js` |
| 44 | "NOW" marker | `static/js/draw/charts.js` |
| 45 | 24-hour strip, scrollable, with a symbol and rain chance per hour | `static/js/panels/forecast.js` |
| 46 | Multi-day forecast with hi/lo bars normalised across all days | `static/js/panels/forecast.js` |
| 47 | Per-day rain chance, precipitation total and peak UV | `static/js/panels/forecast.js` |
| 48 | Rain windows: when it starts, how long, how much, peak chance | `weatherapp/meteorology/timeline.py` |
| 49 | Dry windows long enough to be useful | `weatherapp/meteorology/timeline.py` |
| 50 | Warmest hour, coldest hour and the 24-hour swing | `weatherapp/meteorology/timeline.py` |

## Sun, moon and sea

| # | Feature | Implementation |
|---|---|---|
| 51 | NOAA solar position: elevation and azimuth, live | `weatherapp/meteorology/solar.py` |
| 52 | Sun-path chart with a horizon line and the sun's current place on it | `static/js/draw/charts.js` |
| 53 | Sunrise and sunset, computed, with provider values preferred when present | `weatherapp/services/report_service.py` |
| 54 | Civil dawn and dusk | `weatherapp/meteorology/solar.py` |
| 55 | Solar noon | `weatherapp/meteorology/solar.py` |
| 56 | Golden-hour window | `weatherapp/meteorology/solar.py` |
| 57 | Daylight length, with polar day and polar night handled | `weatherapp/meteorology/solar.py` |
| 58 | Change in daylight versus yesterday, in minutes | `weatherapp/meteorology/solar.py` |
| 59 | Moon phase, age, illuminated percentage and waxing/waning | `weatherapp/meteorology/solar.py` |
| 60 | Sea state for coastal places: wave height, period, swell direction, water temperature | `weatherapp/providers/demo.py`, `weatherapi.py` |

## Air quality

| # | Feature | Implementation |
|---|---|---|
| 61 | US EPA AQI computed from published PM2.5 and PM10 breakpoints | `weatherapp/meteorology/air.py` |
| 62 | AQI category with the matching health guidance | `weatherapp/meteorology/air.py` |
| 63 | Dominant pollutant identified | `weatherapp/meteorology/air.py` |
| 64 | UK DEFRA index and band | `weatherapp/meteorology/air.py` |
| 65 | Six pollutants charted against their reference limits | `static/js/draw/charts.js` |
| 66 | The AQI basis stated on screen, including which pollutants are excluded and why | `weatherapp/meteorology/air.py` |

## Decisions

| # | Feature | Implementation |
|---|---|---|
| 67 | Comfort index 0-100 with an asymmetric hot/cold curve | `weatherapp/advice/comfort.py` |
| 68 | Named detractors with the points each one costs | `weatherapp/advice/comfort.py` |
| 69 | Umbrella verdict with timing: "rain starts in about 40 min" | `weatherapp/advice/guidance.py` |
| 70 | Sunscreen verdict with an estimated burn time | `weatherapp/advice/guidance.py` |
| 71 | Layered outfit recommendation keyed to apparent temperature | `weatherapp/advice/guidance.py` |
| 72 | Contextual extras: waterproof shell, windproof outer, sunglasses | `weatherapp/advice/guidance.py` |
| 73 | Running score, cooler-is-better | `weatherapp/advice/activities.py` |
| 74 | Cycling score, weighting wind and gusts twice as heavily | `weatherapp/advice/activities.py` |
| 75 | Laundry-drying score from warmth, dryness and air movement | `weatherapp/advice/activities.py` |
| 76 | Stargazing score penalising cloud, moonlight and dew | `weatherapp/advice/activities.py` |
| 77 | Beach score, factoring water temperature when known | `weatherapp/advice/activities.py` |
| 78 | Gardening score plus explicit watering advice | `weatherapp/advice/activities.py` |
| 79 | Photography score that prefers broken cloud to a clear sky | `weatherapp/advice/activities.py` |
| 80 | Kite and sail score, where too little wind is the failure | `weatherapp/advice/activities.py` |
| 81 | Every score carries the single biggest reason for it | `weatherapp/advice/registry.py` |
| 82 | Frost and ground-frost risk, using the dew-point margin | `weatherapp/meteorology/timeline.py` |
| 83 | "Open the windows" window, against your own indoor temperature | `weatherapp/meteorology/timeline.py` |
| 84 | Best use of today, picked across every score | `weatherapp/advice/__init__.py` |
| 85 | One-sentence plain-language summary, also used for screen readers | `weatherapp/advice/guidance.py` |
| 86 | Weather warnings with severity tone; in demo mode derived from the forecast so they never contradict the panels | `weatherapp/providers/demo.py`, `weatherapi.py` |

## Personalisation

| # | Feature | Implementation |
|---|---|---|
| 87 | Two full themes (Cyanotype, Draft) plus auto | `static/css/tokens.css` |
| 88 | Metric and imperial presets | `static/js/core/settings.js` |
| 89 | Independent units: temperature, wind (km/h, mph, m/s, knots, Beaufort), pressure (mb, inHg, mmHg), precipitation, distance | `static/js/core/format.js` |
| 90 | 12- or 24-hour clock | `static/js/core/format.js` |
| 91 | Comfortable or compact density | `static/css/tokens.css` |
| 92 | High-contrast mode | `static/css/tokens.css` |
| 93 | Motion preference, honouring `prefers-reduced-motion` by default | `static/css/tokens.css` |
| 94 | Isobar field on or off | `static/js/draw/isobars.js` |
| 95 | Configurable auto-refresh, paused when the tab is hidden or offline | `static/js/main.js` |
| 96 | Indoor temperature setting that feeds the air-out calculation | `static/js/core/settings.js` |
| 97 | Show or hide any panel, remembered between visits | `static/js/main.js` |
| 98 | Export and import preferences as JSON, and reset to defaults | `static/js/core/settings.js` |

## Platform

| # | Feature | Implementation |
|---|---|---|
| 99 | Command palette with actions, saved places and panel toggles | `static/js/ui/palette.js` |
| 100 | Keyboard shortcuts with a help overlay generated from the real bindings | `static/js/ui/shortcuts.js` |

## Also present, beyond the hundred

- Copy the whole report as plain text (`static/js/core/textreport.js`)
- Print stylesheet that drops the furniture and keeps the data
- Installable PWA; service worker with a cache-first shell and
  stale-while-revalidate API
- Offline detection with a banner, and a server-side cache that serves stale
  data rather than an error when the upstream fails
- ETag / 304 conditional GET, plus `Age` and `X-Cache` headers
- `/api/v1/capabilities` and `/api/v1/healthz`
- The v1 `/get_weather` endpoint and the old form POST still work
- Masonry layout that renumbers panels to match reading order
- Skip link, landmarks, live region, visible focus, and an `aria-label` on
  every instrument
- Panel-level error isolation: one broken panel cannot take the sheet down
- All DOM built through `el()`/`svg()`, so API text is never parsed as markup
