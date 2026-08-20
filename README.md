# Barograph

A weather app that answers *"what should I do today?"* rather than just
*"what is the temperature?"* — presented as a technical drawing of the
atmosphere instead of a stack of cards.

It runs with no API key. Without one it serves physically modelled demo data,
so every feature is explorable immediately.

```sh
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
```

## What it does

- **Reads the sky like a chart.** A real synoptic station plot, correct wind
  barbs, a barometer dial, a live isobar field drawn from the pressure
  forecast, and a 48-hour meteogram annotated with drafting callouts.
- **Answers questions.** Do I need an umbrella, and when does the rain start?
  Sunscreen? What should I wear? Is today better for running or for
  photography? When should I open the windows?
- **Shows its work.** Every score names the biggest reason for it. The air
  quality panel states which pollutants it can and cannot convert, and why.
- **Computes rather than fetches.** Solar and lunar geometry come from the NOAA
  algorithm, so sun path, golden hour, daylight length and the change since
  yesterday need no extra API call and work at the poles.

The full list is in [FEATURES.md](FEATURES.md) — 100 features, each with the
file that implements it. The visual language is explained in
[docs/DESIGN.md](docs/DESIGN.md), and the code structure in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Live data

```sh
echo "API_KEY=your_weatherapi_key" > .env
python app.py
```

Get a free key from [weatherapi.com](https://www.weatherapi.com/). With a key
present the app switches to live data automatically; the demo provider is the
fallback, not a mode you have to turn off.

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `API_KEY` | *(none)* | WeatherAPI key. Absent means demo mode. |
| `WEATHER_PROVIDER` | `auto` | `auto`, `weatherapi` or `demo`. |
| `DEFAULT_PLACE` | `London` | Place shown on a bare visit. |
| `FORECAST_DAYS` | `3` | Days requested (WeatherAPI's free tier allows 3). |
| `CACHE_TTL` | `300` | Seconds a report stays fresh. |
| `CACHE_STALE_TTL` | `3600` | How long a stale report may still be served. |
| `HTTP_TIMEOUT` | `8` | Upstream timeout in seconds. |
| `TIME_QUANTUM` | `60` | Bucket size for "now", which keeps ETags stable. |
| `MARINE_ENABLED` | `true` | Request the marine product for coastal places. |

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/report?q=London&days=3` | The full report |
| `GET /api/v1/search?q=lond` | Place suggestions |
| `GET /api/v1/compare?q=London&q=Oslo` | Up to four places at once |
| `GET /api/v1/capabilities` | Version, provider, registered activities |
| `GET /api/v1/healthz` | Health and cache statistics |
| `GET /get_weather?city=London` | The v1 endpoint, unchanged |

Reports send an `ETag`; a matching `If-None-Match` gets a 304. `X-Cache` and
`Age` report cache state, which is deliberately excluded from the ETag so a
cache hit does not invalidate a client's copy.

## Keyboard

`/` search · `⌘K`/`Ctrl+K` command palette · `R` refresh · `U` units ·
`T` theme · `D` density · `C` copy as text · `S` save place · `L` locate ·
`P` print · `?` help

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest -q
```

208 tests. The meteorology is checked against the values the issuing services
publish — NWS heat index and wind chill tables, EPA AQI breakpoints, and solar
geometry against known sunrise times and the polar day/night cases.

## Deploying

`vercel.json` builds `app.py` with `@vercel/python`. `npm start` runs gunicorn.
There is no frontend build step: the browser code is ES modules and plain CSS,
served as written.

## Licence

MIT.
