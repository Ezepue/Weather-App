# Architecture

## Dependency rule

Dependencies point inward. `domain` knows nothing about anything else; `web`
knows everything. No inner layer imports an outer one.

```
web/          delivery: Flask blueprints, serialization, caching headers
  |
  v
services/     orchestration: ReportService builds a Report from a provider
  |
  +--> providers/    adapters: WeatherAPI, Demo, Caching decorator
  |
  +--> advice/       policy: comfort, activity scorers, guidance
  |
  +--> meteorology/  pure functions: thermal indices, air quality, solar, timeline
  |
  v
domain/       models + protocols. Zero dependencies.
```

## Where each SOLID principle is load-bearing

| Principle | Applied as |
|---|---|
| Single responsibility | `meteorology/thermal.py` only converts temperature to felt temperature; `advice/activities.py` only judges activities. Splitting the old `derive.py` was the point. |
| Open/closed | Activity scorers self-register in `advice/registry.py`. Adding "kite surfing" means adding one file-local function with a decorator, and touching nothing else. |
| Liskov substitution | `DemoProvider`, `WeatherAPIProvider` and `CachingProvider` are interchangeable behind `WeatherProvider`; the service cannot tell them apart, including failure modes (all raise `ProviderError`). |
| Interface segregation | `WeatherProvider` has two methods. Nothing that only needs `search()` is forced to depend on report fetching. |
| Dependency inversion | `ReportService` depends on the `WeatherProvider` protocol; `create_app` injects a concrete one chosen by `providers.factory`. Tests inject a stub with no HTTP and a frozen clock. |

## Patterns, and why each one is there

- **Adapter** (`providers/weatherapi.py`) - the upstream JSON shape is not our
  domain shape, and should never leak past this file.
- **Decorator** (`providers/caching.py`) - caching is not the concern of either
  provider. Wrapping means `DemoProvider` gets caching for free and neither
  provider contains a cache lookup.
- **Factory** (`providers/factory.py`) - one place decides demo vs live, so the
  "no API key" fallback is a single branch instead of a scattered condition.
- **Strategy + Registry** (`advice/`) - scorers are uniform callables over one
  input record, so they can be listed, filtered and tested individually.
- **Builder** (`services/report_service.py`) - assembling a `Report` takes six
  ordered steps with interdependencies (solar before advice, advice after air
  quality); the builder makes that order explicit and testable.
- **Injected clock** (`infrastructure/clock.py`) - "now" is an input, not an
  ambient fact, so time-dependent behaviour is deterministic under test.

## Non-goals

No ORM, no DI container, no message bus. There is one data source and no
persistence; adding those layers would be architecture as decoration.
