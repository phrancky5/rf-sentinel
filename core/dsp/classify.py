"""Rule-based signal classification from spectral features + band awareness."""

from __future__ import annotations

import numpy as np

from .bands import lookup_band

FM_BROADCAST = "fm_broadcast"
NARROWBAND_FM = "narrowband_fm"
DIGITAL = "digital"
AM_BROADCAST = "am_broadcast"
CARRIER = "carrier"
AVIATION = "aviation"
HAM = "ham"
ISM = "ism"
GSM = "gsm"
ADSB = "adsb"
UNKNOWN = "unknown"

SHORT_LABELS = {
    FM_BROADCAST: "FM",
    NARROWBAND_FM: "NFM",
    DIGITAL: "DIG",
    AM_BROADCAST: "AM",
    CARRIER: "CW",
    AVIATION: "AIR",
    HAM: "HAM",
    ISM: "ISM",
    GSM: "GSM",
    ADSB: "ADS",
    UNKNOWN: "",
}


def _spectral_flatness(power_linear: np.ndarray) -> float:
    """Geometric mean / arithmetic mean of linear power. 0=tonal, 1=flat."""
    p = power_linear[power_linear > 0]
    if len(p) < 2:
        return 0.0
    log_mean = np.mean(np.log(p))
    return float(np.exp(log_mean) / np.mean(p))


def _occupied_bandwidth_khz(freqs_mhz: np.ndarray, power_linear: np.ndarray) -> float:
    """Bandwidth containing 99% of total power."""
    total = np.sum(power_linear)
    if total <= 0:
        return 0.0
    cumsum = np.cumsum(power_linear)
    lo = np.searchsorted(cumsum, total * 0.005)
    hi = np.searchsorted(cumsum, total * 0.995)
    lo = max(0, lo)
    hi = min(len(freqs_mhz) - 1, hi)
    return float((freqs_mhz[hi] - freqs_mhz[lo]) * 1000)


def _edge_steepness(power_db: np.ndarray, freq_step_khz: float) -> float:
    """Average slope at signal edges in dB/kHz."""
    n = len(power_db)
    if n < 6:
        return 0.0
    edge_bins = max(2, n // 8)
    left_slope = abs(power_db[edge_bins] - power_db[0]) / (edge_bins * freq_step_khz)
    right_slope = abs(power_db[-1] - power_db[-1 - edge_bins]) / (edge_bins * freq_step_khz)
    return float((left_slope + right_slope) / 2)


def _apply_band_prior(freq_mhz: float, signal_type: str, confidence: float) -> tuple[str, float, str | None]:
    """Adjust classification using frequency band knowledge.

    Returns (signal_type, confidence, band_name).
    """
    band = lookup_band(freq_mhz)
    if band is None:
        return signal_type, confidence, None

    expected = band.expected_type

    if signal_type == expected:
        # Spectral and band agree — boost confidence
        return signal_type, min(0.98, confidence + 0.1), band.name

    if signal_type == UNKNOWN:
        # No spectral match but we know the band — use band's expected type
        return expected, 0.55, band.name

    # Spectral says one thing, band says another — trust spectral but note the band
    return signal_type, max(0.3, confidence - 0.1), band.name


def _classify_one(
    freqs_mhz: np.ndarray,
    power_db: np.ndarray,
    peak,
) -> dict:
    """Classify a single peak and return a dict with peak fields + classification."""
    freq_step_khz = float((freqs_mhz[-1] - freqs_mhz[0]) / (len(freqs_mhz) - 1) * 1000)

    bw_khz = getattr(peak, "bandwidth_khz", 0.0)
    prominence = getattr(peak, "prominence_db", 0.0)

    # Slice PSD around peak — wide enough to capture full FM broadcast signals
    window_khz = max(bw_khz * 4, 250.0)
    window_bins = max(4, int(window_khz / freq_step_khz / 2))
    center_idx = int(np.argmin(np.abs(freqs_mhz - peak.freq_mhz)))
    lo = max(0, center_idx - window_bins)
    hi = min(len(freqs_mhz), center_idx + window_bins + 1)

    sl_freqs = freqs_mhz[lo:hi]
    sl_db = power_db[lo:hi]
    sl_linear = 10.0 ** (sl_db / 10.0)

    flatness = _spectral_flatness(sl_linear)
    occ_bw = _occupied_bandwidth_khz(sl_freqs, sl_linear)
    steepness = _edge_steepness(sl_db, freq_step_khz)

    # Rule-based spectral classification
    signal_type = UNKNOWN
    confidence = 0.5

    if (occ_bw > 120 and flatness > 0.3) or (bw_khz > 40 and prominence > 15):
        signal_type = FM_BROADCAST
        confidence = min(0.95, 0.6 + flatness * 0.3 + min(occ_bw / 500, 0.2))
    elif occ_bw < 5 and prominence > 20:
        signal_type = CARRIER
        confidence = min(0.9, 0.5 + (prominence - 20) * 0.02)
    elif 5 <= occ_bw <= 35 and flatness < 0.4:
        signal_type = NARROWBAND_FM
        confidence = 0.6 + (0.4 - flatness) * 0.5
    elif flatness > 0.5 and steepness > 2:
        signal_type = DIGITAL
        confidence = min(0.85, 0.5 + steepness * 0.05 + flatness * 0.2)
    elif 8 <= occ_bw <= 15 and flatness > 0.3:
        signal_type = AM_BROADCAST
        confidence = 0.5

    # Apply band-aware prior
    peak_freq = getattr(peak, "freq_mhz", 0.0)
    signal_type, confidence, band_name = _apply_band_prior(peak_freq, signal_type, confidence)

    return {
        "freq_mhz": round(peak_freq, 4),
        "power_db": round(getattr(peak, "power_db", 0.0), 1),
        "prominence_db": round(prominence, 1),
        "bandwidth_khz": round(bw_khz, 1),
        "signal_type": signal_type,
        "confidence": round(confidence, 2),
        "band": band_name,
    }


def classify_peaks(
    freqs_mhz: np.ndarray,
    power_db: np.ndarray,
    peaks,
) -> list[dict]:
    """Classify a list of peaks and return dicts with signal_type + confidence."""
    if len(freqs_mhz) < 4 or not peaks:
        return []
    return [_classify_one(freqs_mhz, power_db, pk) for pk in peaks]
