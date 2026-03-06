# RF Sentinel — Commands

## Training (`core.ml.train`)

```bash
# Quick test — 10 epochs, 1 fold
python -m core.ml.train --data data/radioml.npz data/synthetic.npz --epochs 10 --rotations 1

# Full — 80 epochs, 5 folds
python -m core.ml.train --data data/radioml.npz data/synthetic.npz --epochs 80
```

## Feature Comparison (`scripts.compare_data`)

```bash
# Per-channel cosine similarity between classes
python -m scripts.compare_data --features --training data/radioml.npz data/synthetic.npz \
    --live data/debug/fm data/debug/noise data/debug/nfm data/debug/am data/debug/ofdm data/debug/tdma

# Raw IQ metrics (SNR, occupancy, PAPR, etc.)
python -m scripts.compare_data --training data/radioml.npz data/synthetic.npz \
    --live data/debug/fm data/debug/noise data/debug/nfm data/debug/am data/debug/ofdm data/debug/tdma
```

## Visual Snippets (`scripts.compare_snippets`)

```bash
# Per-class overlay plots
python -m scripts.compare_snippets --training data/radioml.npz data/synthetic.npz -n 8

# Per-dataset breakdown (RadioML vs synthetic separately)
python -m scripts.compare_snippets --training data/radioml.npz data/synthetic.npz -n 8 --per-data

# Include live captures
python -m scripts.compare_snippets --training data/radioml.npz data/synthetic.npz \
    --live data/debug/fm data/debug/noise data/debug/nfm data/debug/am data/debug/ofdm data/debug/tdma -n 8

# Specific classes only
python -m scripts.compare_snippets --training data/radioml.npz data/synthetic.npz -n 8 -c fm nfm ofdm tdma
```

## Data Generation (`scripts.generate_synthetic`)

```bash
python -m scripts.generate_synthetic --out data/synthetic.npz --per-class 2000
```