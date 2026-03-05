"""Compare raw IQ properties between training data and live SDR captures.

Usage:
    python -m scripts.compare_data --training data/radioml.npz data/subghz.npz data/synthetic.npz \
        --live data/debug/fm data/debug/digital data/debug/noise
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np

from core.ml.model import ML_CLASSES, N_CLASSES


def iq_metrics(iq: np.ndarray) -> dict:
    """Compute raw IQ diagnostic metrics for a single 1024-sample snippet."""
    iq = iq.astype(np.complex128)
    n = len(iq)

    power = np.mean(np.abs(iq) ** 2)
    amp = np.abs(iq)

    S = np.abs(np.fft.fftshift(np.fft.fft(iq))) ** 2
    S_db = 10 * np.log10(np.maximum(S, 1e-30))
    peak_bin = int(np.argmax(S))

    # SNR: peak power vs median power
    median_power = np.median(S)
    snr_db = 10 * np.log10(S[peak_bin] / max(median_power, 1e-30))

    # Spectral occupancy: fraction of bins within 10 dB of peak
    threshold = S_db[peak_bin] - 10
    occupancy = np.mean(S_db > threshold)

    # Frequency offset: peak distance from center (fraction of bandwidth)
    freq_offset = abs(peak_bin - n // 2) / n

    # PAPR: Peak-to-Average Power Ratio
    papr_db = 10 * np.log10(np.max(amp ** 2) / max(power, 1e-30))

    # Noise floor flatness: std of bottom 25% of spectrum
    sorted_s = np.sort(S_db)
    noise_floor_std = np.std(sorted_s[: n // 4])

    # DC spike: ratio of DC bin power to mean
    dc_bin = n // 2
    dc_ratio = S[dc_bin] / max(np.mean(S), 1e-30)

    # IQ balance: ratio of I power to Q power (1.0 = balanced)
    i_power = np.mean(iq.real ** 2)
    q_power = np.mean(iq.imag ** 2)
    iq_balance = i_power / max(q_power, 1e-30)

    # Amplitude distribution: kurtosis (Gaussian=3, constant envelope<3)
    amp_centered = amp - amp.mean()
    amp_std = amp.std() + 1e-12
    kurtosis = np.mean((amp_centered / amp_std) ** 4)

    return {
        "snr_db": snr_db,
        "occupancy": occupancy,
        "freq_offset": freq_offset,
        "papr_db": papr_db,
        "noise_floor_std": noise_floor_std,
        "dc_ratio": dc_ratio,
        "iq_balance": iq_balance,
        "kurtosis": kurtosis,
    }


def load_training(npz_paths: list[str]) -> dict[str, list[np.ndarray]]:
    """Load training data grouped by class label."""
    per_class: dict[str, list[np.ndarray]] = {c: [] for c in ML_CLASSES}
    for path in npz_paths:
        data = np.load(path)
        iq_all = data["iq"]
        labels = data["labels"]
        for i in range(len(labels)):
            cls = ML_CLASSES[labels[i]]
            per_class[cls].append(iq_all[i])
    return per_class


def load_live(debug_dirs: list[str]) -> dict[str, list[np.ndarray]]:
    """Load live captures from data/debug/ subdirs."""
    per_class: dict[str, list[np.ndarray]] = {}
    for d in debug_dirs:
        if not os.path.isdir(d):
            continue
        class_name = os.path.basename(d)
        files = sorted(glob.glob(os.path.join(d, "*.npz")))
        if not files:
            continue
        samples = []
        for f in files:
            data = np.load(f)
            samples.append(data["iq"])
        per_class[class_name] = samples
    return per_class


def summarize(samples: list[np.ndarray], max_n: int = 500) -> dict[str, tuple[float, float]]:
    """Compute mean and std of each metric across samples."""
    if not samples:
        return {}
    rng = np.random.default_rng(42)
    if len(samples) > max_n:
        idx = rng.choice(len(samples), max_n, replace=False)
        samples = [samples[i] for i in idx]

    all_metrics: dict[str, list[float]] = {}
    for s in samples:
        m = iq_metrics(s)
        for k, v in m.items():
            all_metrics.setdefault(k, []).append(v)

    return {k: (np.mean(v), np.std(v)) for k, v in all_metrics.items()}


METRIC_NAMES = ["snr_db", "occupancy", "freq_offset", "papr_db",
                "noise_floor_std", "dc_ratio", "iq_balance", "kurtosis"]
METRIC_FMT = {
    "snr_db": "{:6.1f}",
    "occupancy": "{:5.1%}",
    "freq_offset": "{:6.3f}",
    "papr_db": "{:6.1f}",
    "noise_floor_std": "{:6.2f}",
    "dc_ratio": "{:6.1f}",
    "iq_balance": "{:6.3f}",
    "kurtosis": "{:6.2f}",
}


def print_comparison(training: dict[str, list[np.ndarray]], live: dict[str, list[np.ndarray]]):
    live_classes = sorted(live.keys())
    if not live_classes:
        print("No live captures found.")
        return

    for cls in live_classes:
        print(f"\n{'='*72}")
        print(f"  CLASS: {cls}")
        print(f"{'='*72}")

        live_summary = summarize(live[cls])
        train_summary = summarize(training.get(cls, []))

        # Map debug dir names to training class names
        if not train_summary:
            # Try mapping debug names to training names
            mapping = {"digital": "digital", "noise": "noise"}
            mapped = mapping.get(cls)
            if mapped and mapped in training:
                train_summary = summarize(training[mapped])

        n_live = len(live[cls])
        n_train = len(training.get(cls, []))
        print(f"  Live: {n_live} samples  |  Training: {n_train} samples")

        header = f"  {'Metric':<18s}  {'Live':>14s}  {'Training':>14s}  {'Delta':>8s}"
        print(f"\n{header}")
        print(f"  {'-'*58}")

        for m in METRIC_NAMES:
            if m not in live_summary:
                continue
            l_mean, l_std = live_summary[m]
            fmt = METRIC_FMT[m]
            live_str = f"{fmt.format(l_mean)} ±{fmt.format(l_std).strip()}"

            if m in train_summary:
                t_mean, t_std = train_summary[m]
                train_str = f"{fmt.format(t_mean)} ±{fmt.format(t_std).strip()}"
                delta = l_mean - t_mean
                delta_str = f"{delta:+.2f}"
            else:
                train_str = "  (no data)"
                delta_str = ""

            print(f"  {m:<18s}  {live_str:>14s}  {train_str:>14s}  {delta_str:>8s}")

    # Overall comparison
    print(f"\n{'='*72}")
    print("  KEY DIFFERENCES TO WATCH:")
    print(f"{'='*72}")
    print("  - snr_db:          Live signals much weaker/stronger than training?")
    print("  - occupancy:       Different spectral width = different BW assumptions")
    print("  - freq_offset:     Training centered vs live off-center")
    print("  - dc_ratio:        DC spike from SDR hardware (not in synthetic data)")
    print("  - iq_balance:      Real SDR has IQ imbalance, synthetic doesn't")
    print("  - kurtosis:        Amplitude distribution shape differences")


def main():
    parser = argparse.ArgumentParser(description="Compare training vs live IQ data")
    parser.add_argument("--training", nargs="+", required=True, help="Training .npz files")
    parser.add_argument("--live", nargs="+", required=True, help="Debug capture directories")
    args = parser.parse_args()

    print("Loading training data...")
    training = load_training(args.training)
    for cls in ML_CLASSES:
        print(f"  {cls}: {len(training[cls])} samples")

    print("\nLoading live captures...")
    live = load_live(args.live)
    for cls, samples in live.items():
        print(f"  {cls}: {len(samples)} samples")

    print_comparison(training, live)


if __name__ == "__main__":
    main()
