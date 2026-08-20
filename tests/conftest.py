from datetime import datetime, timezone

import pytest

from weatherapp import create_app
from weatherapp.config import Settings
from weatherapp.infrastructure.clock import FrozenClock
from weatherapp.providers.demo import DemoProvider
from weatherapp.services import ReportService

FIXED_MOMENT = datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc)


@pytest.fixture
def clock():
    return FrozenClock(FIXED_MOMENT)


@pytest.fixture
def settings():
    return Settings(api_key="", provider="demo", forecast_days=3, version="test")


@pytest.fixture
def provider(clock):
    return DemoProvider(clock=clock)


@pytest.fixture
def service(provider, clock, settings):
    return ReportService(provider, clock, settings)


@pytest.fixture
def report(service):
    return service.report("London")


@pytest.fixture
def app(settings, clock):
    from weatherapp.providers import build_provider
    return create_app(settings=settings, provider=build_provider(settings, clock), clock=clock)


@pytest.fixture
def client(app):
    return app.test_client()
