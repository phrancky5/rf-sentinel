"""Frequency band database for band-aware signal classification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BandInfo:
    start_mhz: float
    stop_mhz: float
    name: str
    expected_type: str
    short_label: str


BANDS: list[BandInfo] = [
    BandInfo(87.5, 108.0, "FM Broadcast", "fm_broadcast", "FM"),
    BandInfo(118.0, 137.0, "Airband", "aviation", "AIR"),
    BandInfo(28.0, 29.7, "10m Ham", "ham", "HAM"),
    BandInfo(50.0, 54.0, "6m Ham", "ham", "HAM"),
    BandInfo(144.0, 148.0, "2m Ham", "ham", "HAM"),
    BandInfo(430.0, 440.0, "70cm Ham", "ham", "HAM"),
    BandInfo(1240.0, 1300.0, "23cm Ham", "ham", "HAM"),
    BandInfo(174.0, 230.0, "DAB+", "ofdm", "DAB"),
    BandInfo(380.0, 400.0, "TETRA", "tdma", "TETRA"),
    BandInfo(446.0, 446.2, "PMR446", "narrowband_fm", "PMR"),
    BandInfo(433.05, 434.79, "433 ISM", "ism", "ISM"),
    BandInfo(863.0, 870.0, "868 ISM", "ism", "ISM"),
    BandInfo(935.0, 960.0, "GSM 900 DL", "tdma", "GSM"),
    BandInfo(1089.0, 1091.0, "ADS-B", "adsb", "ADS"),
]

# Sort by start frequency for binary search
BANDS.sort(key=lambda b: b.start_mhz)


def lookup_band(freq_mhz: float) -> BandInfo | None:
    """Find which band a frequency falls in, or None."""
    for band in BANDS:
        if band.start_mhz <= freq_mhz <= band.stop_mhz:
            return band
    return None
