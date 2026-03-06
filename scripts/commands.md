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

# RadioML only vs live
python -m scripts.compare_data --features --training data/radioml.npz \
    --live data/debug/fm data/debug/noise data/debug/nfm data/debug/am data/debug/ofdm data/debug/tdma

# Synthetic only vs live
python -m scripts.compare_data --features --training data/synthetic.npz \
    --live data/debug/fm data/debug/noise data/debug/nfm data/debug/am data/debug/ofdm data/debug/tdma

# Raw IQ metrics (SNR, occupancy, PAPR, etc.)
python -m scripts.compare_data --training data/radioml.npz data/synthetic.npz \
    --live data/debug/fm data/debug/noise data/debug/nfm data/debug/am data/debug/ofdm data/debug/tdma
```

## Visual Snippets (`scripts.compare_snippets`)

```bash
# Per-class overlay plots
python -m scripts.compare_snippets -n 8

# Per-dataset breakdown (RadioML vs synthetic separately)
python -m scripts.compare_snippets -n 8 --per-data

# Include live captures
python -m scripts.compare_snippets \
    --live data/debug/fm data/debug/noise data/debug/nfm data/debug/am data/debug/ofdm data/debug/tdma -n 8

# Specific classes only
python -m scripts.compare_snippets -n 8 -c fm nfm ofdm tdma
```

## Source Comparison (`scripts.compare_sources`)

```bash
# Compare RadioML FM vs live FM
python -m scripts.compare_sources --training data/radioml.npz --class fm --live data/debug/fm

# Compare synthetic FM vs live FM
python -m scripts.compare_sources --training data/synthetic.npz --class fm --live data/debug/fm
```

## Data Generation — Synthetic (Docker + TorchSig)

```bash
MSYS_NO_PATHCONV=1 docker run --rm --gpus all \
    -v ./data:/data -v ./scripts:/scripts \
    torchsig-gpu python /scripts/generate_torchsig.py --output /data/synthetic.npz --workers 5
```

## Data Generation — Lightweight (`scripts.generate_synthetic`)

```bash
python -m scripts.generate_synthetic --out data/synthetic.npz --per-class 2000
```

## RadioML Conversion (`scripts.convert_radioml`)

```bash
python scripts/convert_radioml.py \
    --input "core/ml/RadioML 201801a/GOLD_XYZ_OSC.0001_1024.hdf5" \
    --output data/radioml.npz \
    --samples-per-class 5000 \
    --min-snr -6
```