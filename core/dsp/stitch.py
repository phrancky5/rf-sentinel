"""Spectrum stitching — plan, trim, and assemble multi-chunk captures."""

from __future__ import annotations

import numpy as np

from core.dsp.types import SpectrumResult, WaterfallResult


SAMPLE_RATE = 2.048e6           # Fixed sample rate for all captures
USABLE_BW_FRAC = 0.80           # Use 80% of bandwidth (trim noisy edges)
STEP_HZ = SAMPLE_RATE * USABLE_BW_FRAC  # ~1.638 MHz per step


def plan_chunks(start_hz: float, stop_hz: float) -> list[float]:
    """Return center frequencies (Hz) that cover start→stop with edge trimming."""
    span = stop_hz - start_hz
    if span <= SAMPLE_RATE:
        return [(start_hz + stop_hz) / 2]

    centers = []
    fc = start_hz + SAMPLE_RATE / 2
    while fc - SAMPLE_RATE / 2 < stop_hz:
        centers.append(fc)
        fc += STEP_HZ
    return centers


def trim_spectrum(result: SpectrumResult, trim_frac: float = 0.10) -> SpectrumResult:
    """Trim the outer edges of a spectrum to remove rolloff artifacts."""
    n = len(result.freqs_mhz)
    cut = int(n * trim_frac)
    if cut == 0:
        return result
    return SpectrumResult(
        freqs_mhz=result.freqs_mhz[cut:-cut],
        power_db=result.power_db[cut:-cut],
        center_freq_mhz=result.center_freq_mhz,
        sample_rate=result.sample_rate,
    )


def stitch_spectra(segments: list[SpectrumResult]) -> SpectrumResult:
    """Stitch multiple trimmed PSD segments into one continuous spectrum."""
    if len(segments) == 1:
        return segments[0]

    all_freqs = np.concatenate([s.freqs_mhz for s in segments])
    all_power = np.concatenate([s.power_db for s in segments])

    order = np.argsort(all_freqs)
    all_freqs = all_freqs[order]
    all_power = all_power[order]

    return SpectrumResult(
        freqs_mhz=all_freqs,
        power_db=all_power,
        center_freq_mhz=(all_freqs[0] + all_freqs[-1]) / 2,
        sample_rate=segments[0].sample_rate,
    )


def trim_waterfall(result: WaterfallResult, trim_frac: float = 0.10) -> WaterfallResult:
    """Trim the outer edges of a waterfall to remove rolloff artifacts."""
    n = len(result.freqs_mhz)
    cut = int(n * trim_frac)
    if cut == 0:
        return result
    return WaterfallResult(
        freqs_mhz=result.freqs_mhz[cut:-cut],
        times=result.times,
        power_db=result.power_db[cut:-cut, :],
        mean_psd_db=result.mean_psd_db[cut:-cut],
        center_freq_mhz=result.center_freq_mhz,
    )


def stitch_waterfalls(segments: list[WaterfallResult]) -> WaterfallResult:
    """Stitch multiple waterfall segments along the frequency axis.

    Each segment was captured sequentially, so the time axis represents
    time-within-chunk. Segments must be sorted by ascending center freq.
    """
    if len(segments) == 1:
        return segments[0]

    min_time_bins = min(s.power_db.shape[1] for s in segments)
    times = segments[0].times[:min_time_bins]

    all_freqs = np.concatenate([s.freqs_mhz for s in segments])
    all_power = np.concatenate([s.power_db[:, :min_time_bins] for s in segments], axis=0)
    all_psd = np.concatenate([s.mean_psd_db for s in segments])

    order = np.argsort(all_freqs)
    return WaterfallResult(
        freqs_mhz=all_freqs[order],
        times=times,
        power_db=all_power[order, :],
        mean_psd_db=all_psd[order],
        center_freq_mhz=(all_freqs[0] + all_freqs[-1]) / 2,
    )
