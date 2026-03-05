# RFSentinel

**Open-source RF spectrum monitoring & signal classification platform**

RTL-SDR based tool for real-time RF spectrum analysis, signal detection, and automatic classification.

![RFSentinel scanning the FM broadcast band](showcase1.png)
![RFSentinel signal detection](showcase2.png)

## Quick Start

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the backend (SDR required)
python -m core.api.server

# In a second terminal, start the frontend
cd frontend
npm install
npm run dev

# Open http://localhost:5173
```

## Requirements

- **Hardware:** RTL-SDR Blog V4 (or compatible)
- **OS:** Windows 10/11, Linux
- **Python:** 3.10+
- **Node.js:** 18+ (for frontend)

## Features

### Live Mode

Continuous real-time spectrum display with signal detection:

- Live-updating power spectrum with scrolling waterfall spectrogram
- Max-hold trace (decaying peak envelope)
- Temporal PSD smoothing (EMA) for stable display and better weak-signal visibility
- Peak tracking across frames with confirmation logic — eliminates jitter
- Click-to-tune VFO marker with draggable repositioning
- FM/AM audio demodulation streamed as PCM over WebSocket
- Drag-to-pan and scroll-to-zoom on the frequency axis
- Dual-thumb range sliders for both axes

### Scan Mode

Captures a spectrum + waterfall over a frequency range, stitching multiple chunks for wide sweeps (>1.6 MHz bandwidth per chunk, 80% usable with edge trimming). Full-resolution 1D spectrum with decimated 2D waterfall for web delivery. Scan history persisted in SQLite — browse, re-view, or delete past scans. Running scans can be cancelled.

### Signal Detection

Adaptive noise floor estimation with threshold-then-segment peak finding:

- Rolling 25th-percentile filter (501-bin window) — robust in dense signal environments
- Contiguous above-threshold regions merged across small gaps (≤50 kHz), capped at 300 kHz bandwidth
- Max-hold peak detection: runs find_peaks on max PSD from waterfall to catch brief/intermittent transmissions missed by time-averaged spectrum
- Transient peak filtering — requires confirmation across multiple frames before promoting to stable peak
- Auto-scaling peak limit based on scan bandwidth (5 peaks/MHz)
- Peaks ranked by SNR (prominence above local noise floor)

### Signal Classification

Hybrid rule-based + ML classification with band-aware confidence adjustment:

**Rule-based (spectral/temporal features):**

- Spectral features: flatness, occupied bandwidth (99% power), edge steepness
- Temporal features from waterfall: duty cycle (fraction of time active) and power variance to distinguish bursty voice comms from continuous broadcasts
- Band database: FM/AM broadcast, airband, ham bands, PMR446, ISM 433/868, GSM 900, ADS-B
- Band prior promotes narrowband detections to band-specific types (e.g. NFM on airband → aviation)

**ML classifier (1D CNN on IQ samples):**

- 12-class modulation recognition: FM, AM, SSB, CW, NFM, DMR, P25, D-STAR, LoRa, POCSAG, digital (PSK/QAM/OFDM), noise
- 6-channel input features: I, Q, log-magnitude spectrum, instantaneous frequency, amplitude envelope, autocorrelation
- 5-layer 1D CNN (128 filters, ~238K params) exported to ONNX for fast inference
- Active in live mode; rule-based path used in scan mode (which has richer temporal features)

### Frontend

- uPlot-based spectrum chart with colored peak markers per signal type
- Signal list sidebar — sortable, color-coded, click to tune live
- Scan history panel — browse past scans, view results, delete entries
- Waterfall spectrogram with contrast slider
- Preset buttons for common bands (FM, airband, ham, ISM)
- Real-time log console and job history via WebSocket

## Data Sources

This project uses the following datasets for training:

| Dataset                | Description                                                                                                                                   | Source                                                                                                                                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **RadioML 2018.01a**   | 2.55M synthetic IQ samples across 24 modulations (PSK, QAM, AM, FM, SSB, OOK, GMSK, OQPSK) at SNR -20 to +30 dB. 1024 IQ samples per example. | T. O'Shea, T. Roy, T. Clancy. "Over-the-Air Deep Learning Based Radio Signal Classification," IEEE JSAC, 2018. Available on [Kaggle](https://www.kaggle.com/datasets/pinxau1000/radioml-2018-01a). |
| **Sub-GHz IQ Dataset** | Real IQ captures of LoRa (SF7/SF12), IEEE 802.11ah, IEEE 802.15.4g (SUN-OFDM), Sigfox, and noise at 864/867 MHz using USRP B210.              | M. Alhazmi et al., IEEE DataPort. Available on [IEEE DataPort](https://ieee-dataport.org/documents/sub-ghz-iq-dataset).                                                                            |
| **TorchSig**           | Synthetic RF signal generation library with 57+ modulation types and realistic channel impairments (fading, frequency offset, phase noise).   | TorchDSP. Available on [GitHub](https://github.com/TorchDSP/torchsig).                                                                                                                             |

Custom numpy-based generators are used for protocol-specific signals not covered by the above datasets: CW (Morse OOK), DMR (4GFSK), P25 (C4FM), D-STAR (GMSK), LoRa (CSS chirps), and POCSAG (2FSK).

## License

MIT
