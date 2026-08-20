"""Conversions. Canonical storage is metric; conversion happens at the edges."""

from __future__ import annotations


def c_to_f(c: float) -> float:
    return c * 9 / 5 + 32


def f_to_c(f: float) -> float:
    return (f - 32) * 5 / 9


def kph_to_mph(kph: float) -> float:
    return kph * 0.621371


def kph_to_ms(kph: float) -> float:
    return kph / 3.6


def kph_to_knots(kph: float) -> float:
    return kph * 0.539957


def mb_to_inhg(mb: float) -> float:
    return mb * 0.0295300


def mb_to_mmhg(mb: float) -> float:
    return mb * 0.750062


def mm_to_inches(mm: float) -> float:
    return mm / 25.4


def km_to_miles(km: float) -> float:
    return km * 0.621371
