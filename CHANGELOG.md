# Changelog

All notable changes to this fork of RF-Sentinel are documented here.

---

## [0.2.0-MAX] — 2026-03-29

### Added

#### Hardware
- **HackRF One support** — new `hackrf` SDR driver (`core/sdr/hackrf_device.py`) using the `pyhackrf2` library. Covers 1 MHz – 6 GHz with LNA + VGA gain mapping. Supports capture, live streaming, retune, and bias-T.
- **Bundled HackRF DLLs** — `hackrf.dll`, `libusb-1.0.dll`, and `pthreadVC2.dll` shipped in `core/sdr/libs/` (~300 KB). A runtime bootstrap in `hackrf_device.py` registers the directory via `os.add_dll_directory()` and monkey-patches `ctypes.CDLL` to translate the Linux `.so` name used by `pyhackrf2` to the Windows DLL. No system-wide driver install required.
- **Multi-device enumeration** — `GET /api/devices` probes all connected RTL-SDR and HackRF devices, returning type, index, label, and serial for each. Multiple devices of the same type are fully supported.
- **Device selector with index** — the ControlPanel shows two dropdowns: SDR type (RTL-SDR / HackRF) and device instance (filtered by type). A ⟳ refresh button re-scans the bus.
- **Persistent device aliases** — custom device names can be assigned in the Settings panel (Devices tab), which shows each device's serial number for identification. Aliases are stored by serial in a `device_aliases` SQLite table and shown in the ControlPanel selector. `POST /api/devices/alias` upserts or deletes aliases.
- **Device-aware frequency/gain limits** — frequency inputs and gain slider dynamically adjust their min/max based on the selected device (RTL-SDR: 24–1766 MHz / 0–50 dB, HackRF: 1–6000 MHz / 0–50 dB).

### Changed
- **SDR module refactored** — `core/sdr/__init__.py` is now a factory (`create_device(device_type, device_index)`) with shared `CaptureConfig`/`CaptureResult` types and an `enumerate_devices()` function. The original RTL-SDR code lives in `core/sdr/rtlsdr_device.py`.
- `ScanRequest` and `LiveRequest` models accept `device` (`"rtlsdr"` / `"hackrf"`) and `device_index` (default `0`) fields.
- API frequency limits widened to 1–6000 MHz and gain limit to 62 dB to accommodate HackRF range.
- `JobRunner._capture_segments()` and `LiveSession._loop()` pass `device_index` through the device factory.
- Added `pyhackrf2>=1.0.0` to `requirements.txt` and `pyproject.toml`.
- **Settings panel** now has four tabs: Colors, Markers, Display, and Devices.

### Fixed
- **HackRF scan hang** — `read_samples()` in pyhackrf2 does a full `start_rx`/`stop_rx` cycle per call; the USB transfer pipeline didn't drain cleanly between calls, causing the second chunk to hang. Fixed by closing and reopening the device between retune steps in scan mode.
- **HackRF live streaming** — replaced the `read_samples()` polling loop with a single `start_rx(pipe_function=…)` session that stays open for the entire live duration. Raw I/Q bytes are accumulated and delivered as complex-float numpy chunks via callback.
- **pyhackrf2 `__del__` access-violation spam** — pyhackrf2's `close()` has a typo (`self.device_opened` instead of `self._device_opened`), causing `__del__` to double-close freed pointers. Suppressed by setting `_device_opened = False` after each explicit close.

---

## [0.1.0] — 2026-03-27 (fork baseline)

### Added

#### Hardware
- **Bias-T support** — `bias_tee: bool` parameter wired through the full stack: `CaptureConfig`, `ScanRequest`, `LiveRequest`, `LiveSession` (start / retune / _loop), `runner.py`, and the frontend ControlPanel toggle (yellow ⚡ ON/OFF button below Gain slider).

#### Spectrum / Visualization
- **Peak frequency markers** — automatic local-minima detection on the spectrum with adaptive windowing and greedy NMS. Renders amber dashed lines, ▼ triangles, and rotated frequency labels at the top of the chart (`peakMarkerPlugin.ts`).
- **Marker snap** — clicking the live or scan chart snaps to the nearest detected marker frequency when within `max(0.03 MHz, 6 × bin_step)`, otherwise snaps to the nearest bin.
- **Live chart click-to-retune** — clicking on the live spectrum recenters the SDR, updates Center Freq in the sidebar, and moves the VFO marker.

#### Settings
- **Settings panel** — ⚙ drawer with three tabs:
  - *Colors*: spectrum line/fill, max-hold, VFO, grid, axis, accent, background, marker colors (9 color pickers).
  - *Markers*: minimum prominence (dB) and minimum spacing (MHz) sliders.
  - *Display*: UI font size, marker text size, axis tick text size, axis label text size.
- **SQLite settings persistence** — `/api/settings` GET/POST backed by a `settings` key-value table. Settings are loaded on startup and saved on every change.
- **Live axis/color theming** — chart recreates when axis font or color settings change; marker plugin color updates without recreate.

#### Scan Metadata
- **Scan notes** — editable note field per scan, stored in the `scans.note` column; updated via `PATCH /api/scans/{id}/note`.
- **Preset band tagging** — `scans.preset_band` column stores the active preset when a scan is submitted; displayed as a cyan badge in JobList and ScanMetaPanel.
- **Click-to-prefill** — single-click on a scan result spectrum prefills the Save Frequency form with the clicked frequency.
- **Double-click to go live** — double-click on a scan result spectrum switches to live mode centered at that frequency.

#### Saved Frequencies
- **SQLite `saved_frequencies` table** — CRUD via `GET/POST /api/frequencies` and `DELETE /api/frequencies/{id}`.
- **Save Frequency form** — in ResultView ScanMetaPanel: freq_mhz + description fields, Save button, per-scan list of saved frequencies with delete.
- **Live mode picker** — "Saved Frequencies" dropdown in ControlPanel live mode reloads frequencies and sets Center Freq on selection.

#### UI / UX
- **Collapsible Jobs section** — the JOBS panel in the sidebar can be collapsed/expanded.
- **Version from config** — app version shown in the header is sourced from `frontend/src/config.ts` (single place to update on release).

### Changed
- `PresetBar.onSelect` callback now includes the preset `label` as a third argument; `findPresetLabel()` exported as a helper.
- `SpectrumChart` accepts `onFreqDoubleClick` prop (separate from `onFreqClick`).
- `vfoPlugin` extended with `dblCbRef` and `snapFreqRef` parameters.
- `AppContext` exposes `updateJobInState` and `handleScanPeakClick` to consumers.

### Fixed
- **`VFO_COLOR` runtime crash** — `ReferenceError: VFO_COLOR is not defined` at SpectrumChart.tsx caused by an accidentally stripped import; restored `import { VFO_COLOR } from './theme'`.
