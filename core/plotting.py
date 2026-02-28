"""Plotting utilities for spectrum and waterfall visualization."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np

from core.dsp import downsample_2d


def render_scan_plot(data, params: dict, path: Path, peaks=None) -> None:
    """Render a dark-theme PSD plot with optional peak annotations."""
    fig, ax = plt.subplots(figsize=(14, 4))
    fig.patch.set_facecolor("#0a0e1a")
    ax.set_facecolor("#0f1525")

    freqs = data.freqs_mhz if hasattr(data, 'freqs_mhz') else data["freqs_mhz"]
    power = data.power_db if hasattr(data, 'power_db') else data["power_db"]

    ax.plot(freqs, power, linewidth=0.5, color="#00d4ff")
    ax.fill_between(freqs, np.min(power), power, alpha=0.12, color="#00d4ff")

    if peaks:
        for pk in peaks:
            ax.plot(pk.freq_mhz, pk.power_db, 'v', color='#ff6b35',
                    markersize=6, markeredgecolor='#ff6b35', markeredgewidth=0.5)
            ax.annotate(
                f"{pk.freq_mhz:.3f}",
                xy=(pk.freq_mhz, pk.power_db),
                xytext=(0, 8), textcoords='offset points',
                fontsize=6, color='#ff6b35', ha='center',
                fontweight='bold',
            )

    ax.set_xlabel("Frequency [MHz]", color="#a0a0a0")
    ax.set_ylabel("Power [dB]", color="#a0a0a0")

    n_peaks = len(peaks) if peaks else 0
    title = f"PSD — {params['start_mhz']:.1f}–{params['stop_mhz']:.1f} MHz"
    if n_peaks:
        title += f"  ({n_peaks} signal{'s' if n_peaks != 1 else ''})"
    ax.set_title(title, color="#e0e0e0", fontsize=13, fontweight="bold")

    ax.tick_params(colors="#808080")
    ax.grid(True, alpha=0.15, color="#ffffff")
    ax.set_xlim(freqs[0], freqs[-1])
    for spine in ax.spines.values():
        spine.set_color("#2a2a3a")

    plt.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def render_waterfall_plot(data, params: dict, path: Path, peaks=None) -> None:
    """Render a dark-theme waterfall plot (PSD on top, spectrogram below)."""
    freqs = data.freqs_mhz if hasattr(data, 'freqs_mhz') else data["freqs_mhz"]
    times = data.times if hasattr(data, 'times') else data["times"]
    power = data.power_db if hasattr(data, 'power_db') else data["power_db"]
    psd = data.mean_psd_db if hasattr(data, 'mean_psd_db') else data["mean_psd_db"]

    power_ds = downsample_2d(power, max_freq=2048, max_time=1024)
    nf_ds, nt_ds = power_ds.shape
    freqs_ds = np.linspace(freqs[0], freqs[-1], nf_ds)
    times_ds = np.linspace(times[0], times[-1], nt_ds)

    step_psd = max(1, len(psd) // 2048)
    psd_ds = psd[:len(psd) // step_psd * step_psd].reshape(-1, step_psd).mean(axis=1)
    freqs_psd = np.linspace(freqs[0], freqs[-1], len(psd_ds))

    fig, (ax_psd, ax_wf) = plt.subplots(
        2, 1, figsize=(14, 8),
        gridspec_kw={"height_ratios": [1, 3]}, sharex=True,
    )
    fig.patch.set_facecolor("#0a0e1a")

    for ax in (ax_psd, ax_wf):
        ax.set_facecolor("#0f1525")
        ax.tick_params(colors="#808080")
        ax.grid(True, alpha=0.15, color="#ffffff")
        for spine in ax.spines.values():
            spine.set_color("#2a2a3a")

    ax_psd.plot(freqs_psd, psd_ds, linewidth=0.8, color="#00d4ff")
    ax_psd.fill_between(freqs_psd, np.min(psd_ds), psd_ds, alpha=0.15, color="#00d4ff")

    if peaks:
        for pk in peaks:
            ax_psd.plot(pk.freq_mhz, pk.power_db, 'v', color='#ff6b35',
                        markersize=5, markeredgewidth=0.5)
            ax_psd.annotate(
                f"{pk.freq_mhz:.3f}",
                xy=(pk.freq_mhz, pk.power_db),
                xytext=(0, 7), textcoords='offset points',
                fontsize=5, color='#ff6b35', ha='center',
                fontweight='bold',
            )

    ax_psd.set_ylabel("Power [dB]", color="#a0a0a0")

    n_peaks = len(peaks) if peaks else 0
    title = f"Waterfall — {params['start_mhz']:.1f}–{params['stop_mhz']:.1f} MHz"
    if n_peaks:
        title += f"  ({n_peaks} signal{'s' if n_peaks != 1 else ''})"
    ax_psd.set_title(title, color="#e0e0e0", fontsize=13, fontweight="bold")

    vmin = np.percentile(power_ds, 5)
    vmax = np.percentile(power_ds, 99)
    ax_wf.pcolormesh(
        freqs_ds, times_ds, power_ds.T,
        shading="auto", cmap="inferno",
        norm=Normalize(vmin=vmin, vmax=vmax),
    )
    ax_wf.set_ylabel("Time [s]", color="#a0a0a0")
    ax_wf.set_xlabel("Frequency [MHz]", color="#a0a0a0")

    plt.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)

    del power_ds, freqs_ds, times_ds, psd_ds, freqs_psd
    gc.collect()
