"""DSP module — spectrum analysis, PSD, waterfall, and peak detection."""

from __future__ import annotations

from core.dsp.peaks import SignalPeak, find_peaks  # noqa: F401

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.signal import welch, spectrogram

from core.sdr import CaptureResult


@dataclass
class SpectrumResult:
    """Power spectral density result."""

    freqs_mhz: np.ndarray  # Frequency axis in MHz
    power_db: np.ndarray  # Power in dB
    center_freq_mhz: float
    sample_rate: float


@dataclass
class WaterfallResult:
    """Spectrogram / waterfall result."""

    freqs_mhz: np.ndarray  # Frequency axis in MHz
    times: np.ndarray  # Time axis in seconds
    power_db: np.ndarray  # 2D power array [freq x time] in dB
    mean_psd_db: np.ndarray  # Time-averaged PSD in dB
    center_freq_mhz: float


def compute_psd(
    capture: CaptureResult,
    nfft: int = 4096,
) -> SpectrumResult:
    """Compute power spectral density using Welch method.

    Args:
        capture: CaptureResult from SDR device.
        nfft: FFT size (higher = better frequency resolution, slower).

    Returns:
        SpectrumResult with frequency and power arrays.
    """
    fs = capture.config.sample_rate
    fc = capture.config.center_freq

    freqs, psd = welch(capture.samples, fs=fs, nperseg=nfft, return_onesided=False)
    freqs = np.fft.fftshift(freqs)
    psd = np.fft.fftshift(psd)

    freqs_mhz = (freqs + fc) / 1e6
    power_db = 10 * np.log10(psd + 1e-12)

    return SpectrumResult(
        freqs_mhz=freqs_mhz,
        power_db=power_db,
        center_freq_mhz=fc / 1e6,
        sample_rate=fs,
    )


# ── Stitching ───────────────────────────────────────────

SAMPLE_RATE = 2.048e6          # Fixed sample rate for all captures
USABLE_BW_FRAC = 0.80          # Use 80% of bandwidth (trim noisy edges)
STEP_HZ = SAMPLE_RATE * USABLE_BW_FRAC  # ~1.638 MHz per step


def plan_chunks(start_hz: float, stop_hz: float) -> list[float]:
    """Plan center frequencies for stitched capture.

    Returns list of center frequencies (Hz) that cover start→stop
    using STEP_HZ steps with edge trimming.
    """
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
    """Stitch multiple trimmed PSD segments into one continuous spectrum.

    Segments must be sorted by frequency (ascending center freq).
    Overlapping regions are averaged.
    """
    if len(segments) == 1:
        return segments[0]

    all_freqs = np.concatenate([s.freqs_mhz for s in segments])
    all_power = np.concatenate([s.power_db for s in segments])

    # Sort by frequency
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

    Each segment was captured sequentially (not simultaneously), so the
    time axis represents time-within-chunk, not absolute time.
    Segments must be sorted by frequency (ascending center freq).
    """
    if len(segments) == 1:
        return segments[0]

    # Resample all segments to the same number of time bins (use minimum)
    min_time_bins = min(s.power_db.shape[1] for s in segments)
    times = segments[0].times[:min_time_bins]

    all_freqs = []
    all_power = []
    all_psd = []

    for s in segments:
        all_freqs.append(s.freqs_mhz)
        all_power.append(s.power_db[:, :min_time_bins])
        all_psd.append(s.mean_psd_db)

    freqs = np.concatenate(all_freqs)
    power = np.concatenate(all_power, axis=0)
    psd = np.concatenate(all_psd)

    # Sort by frequency
    order = np.argsort(freqs)
    freqs = freqs[order]
    power = power[order, :]
    psd = psd[order]

    return WaterfallResult(
        freqs_mhz=freqs,
        times=times,
        power_db=power,
        mean_psd_db=psd,
        center_freq_mhz=(freqs[0] + freqs[-1]) / 2,
    )


# ── Waterfall ───────────────────────────────────────────

def compute_waterfall(
    capture: CaptureResult,
    nfft: int = 1024,
) -> WaterfallResult:
    """Compute spectrogram (waterfall) from captured I/Q samples.

    Args:
        capture: CaptureResult from SDR device.
        nfft: FFT size per time slice.

    Returns:
        WaterfallResult with 2D time-frequency power data.
    """
    fs = capture.config.sample_rate
    fc = capture.config.center_freq

    freqs, times, Sxx = spectrogram(
        capture.samples,
        fs=fs,
        nperseg=nfft,
        noverlap=nfft // 2,
        return_onesided=False,
        mode="psd",
    )

    freqs = np.fft.fftshift(freqs)
    Sxx = np.fft.fftshift(Sxx, axes=0)

    freqs_mhz = (freqs + fc) / 1e6
    power_db = 10 * np.log10(Sxx + 1e-12)
    mean_psd_db = np.mean(power_db, axis=1)

    return WaterfallResult(
        freqs_mhz=freqs_mhz,
        times=times,
        power_db=power_db,
        mean_psd_db=mean_psd_db,
        center_freq_mhz=fc / 1e6,
    )
