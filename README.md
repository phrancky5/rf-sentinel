# RFSentinel

**Open-source RF spectrum monitoring & signal classification platform**

RTL-SDR based tool for real-time RF spectrum analysis, signal detection, and automatic classification.

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

Continuous real-time spectrum display. The SDR streams I/Q samples and the frontend renders a live-updating power spectrum with a scrolling waterfall spectrogram below:
- Max-hold trace (decaying peak envelope)
- Click-to-tune VFO marker with draggable repositioning
- Drag-to-pan and scroll-to-zoom on the frequency axis
- Dual-thumb range sliders for both axes
- dB range markers showing min/max power over a 30-second sliding window
- FM audio demodulation via click-to-tune, streamed as PCM over WebSocket

### Scan

Captures a spectrum + waterfall over a frequency range, stitching multiple chunks for wide sweeps. Results render as an interactive spectrum chart (mean PSD with peak detection) above a waterfall spectrogram with a contrast slider. Both charts share a synchronized frequency axis with zoom and pan.

## License

MIT
