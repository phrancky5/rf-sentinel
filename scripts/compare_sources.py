"""Compare feature channels between data sources for the same class.

Shows per-channel cosine similarity and magnitude ratio between two sources
of the same signal type (e.g. RadioML FM vs live FM).

Usage:
    python -m scripts.compare_sources \
        --training data/radioml.npz --class fm \
        --live data/debug/fm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.ml.features import N_IQ, iq_to_channels
from core.ml.model import ML_CLASSES

CHANNEL_NAMES = [
    "I", "Q", "instfreq", "amp", "ifreq_var", "cyclo",
    "spec_1M", "spec_200k", "spec_delta", "spec_25k",
    "acf_full", "acf_200k", "ifreq_acf", "env_var",
    "ifreq_hist", "papr",
]


def _load_class_samples(npz_path: str, cls: str, max_n: int = 200) -> list[np.ndarray]:
    class_to_idx = {c: i for i, c in enumerate(ML_CLASSES)}
    idx = class_to_idx[cls]
    data = np.load(npz_path)
    iq, labels = data["iq"], data["labels"]
    mask = labels == idx
    samples = iq[mask]
    if len(samples) > max_n:
        rng = np.random.default_rng(42)
        samples = samples[rng.choice(len(samples), max_n, replace=False)]
    return [s[:N_IQ] for s in samples]


def _load_live_samples(folder: str) -> list[np.ndarray]:
    p = Path(folder)
    samples = []
    for f in sorted(p.glob("*.npz")):
        data = np.load(f)
        iq = data["iq"]
        if np.iscomplexobj(iq) and len(iq) >= N_IQ:
            samples.append(iq[:N_IQ])
    return samples


def _compute_features(samples: list[np.ndarray]) -> np.ndarray:
    feats = np.stack([iq_to_channels(s) for s in samples])
    return feats


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm < 1e-12:
        return 0.0
    return float(dot / norm)


def main():
    parser = argparse.ArgumentParser(description="Compare feature channels between sources")
    parser.add_argument("--training", type=str, nargs="+", required=True,
                        help="Training .npz file(s)")
    parser.add_argument("--class", dest="cls", type=str, required=True,
                        help="Class name to compare (e.g. fm)")
    parser.add_argument("--live", type=str, required=True,
                        help="Live capture folder")
    parser.add_argument("--max-samples", type=int, default=200)
    args = parser.parse_args()

    print(f"\nComparing '{args.cls}' between training and live\n")

    # Load training samples
    train_samples = []
    for npz in args.training:
        s = _load_class_samples(npz, args.cls, args.max_samples)
        print(f"  Training {npz}: {len(s)} samples")
        train_samples.extend(s)

    # Load live samples
    live_samples = _load_live_samples(args.live)
    print(f"  Live {args.live}: {len(live_samples)} samples")

    if not train_samples or not live_samples:
        print("Need samples from both sources.")
        return

    # Compute features
    print("\nComputing features...")
    train_feats = _compute_features(train_samples)  # (N, 16, 1024)
    live_feats = _compute_features(live_samples)

    train_mean = train_feats.mean(axis=0)  # (16, 1024)
    live_mean = live_feats.mean(axis=0)
    train_std = train_feats.std(axis=0)
    live_std = live_feats.std(axis=0)

    # Per-channel comparison
    print(f"\n{'Channel':<12} {'Cosine':>8} {'MagRatio':>10} {'TrainStd':>10} {'LiveStd':>10}")
    print("-" * 52)

    sims = []
    for ch in range(len(CHANNEL_NAMES)):
        t = train_mean[ch]
        l = live_mean[ch]
        cos = _cosine_sim(t, l)
        t_mag = np.linalg.norm(t)
        l_mag = np.linalg.norm(l)
        ratio = t_mag / l_mag if l_mag > 1e-12 else float("inf")
        t_std_mean = train_std[ch].mean()
        l_std_mean = live_std[ch].mean()
        sims.append(cos)
        print(f"{CHANNEL_NAMES[ch]:<12} {cos:>8.4f} {ratio:>10.3f} {t_std_mean:>10.4f} {l_std_mean:>10.4f}")

    print(f"\nMean cosine similarity: {np.mean(sims):.4f}")
    best = np.argmax(sims)
    worst = np.argmin(sims)
    print(f"Best match:  {CHANNEL_NAMES[best]} ({sims[best]:.4f})")
    print(f"Worst match: {CHANNEL_NAMES[worst]} ({sims[worst]:.4f})")


if __name__ == "__main__":
    main()
