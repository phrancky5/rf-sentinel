"""HackRF One device driver — capture I/Q samples via pyhackrf2."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from core.sdr import CaptureConfig, CaptureResult

log = logging.getLogger(__name__)

# HackRF minimum sample rate (hardware limit)
_MIN_SAMPLE_RATE = 2e6

# ---------------------------------------------------------------------------
# Windows DLL bootstrap for pyhackrf2
# ---------------------------------------------------------------------------
# pyhackrf2's cinterface.py hardcodes LIBNAME = "libhackrf.so.0" (Linux).
# On Windows the native library is hackrf.dll, and Python 3.8+ won't find
# DLLs unless their directory is explicitly registered.
#
# We ship the required DLLs in  core/sdr/libs/  (hackrf.dll, libusb-1.0.dll,
# pthreadVC2.dll) so a fresh install works without PothosSDR or any other
# external package.  The helper below:
#   1. Registers  core/sdr/libs/  as a DLL search directory.
#   2. Temporarily monkey-patches ctypes.CDLL so the Linux .so name is
#      transparently replaced with "hackrf.dll" — this survives pip
#      reinstalls of pyhackrf2.
# ---------------------------------------------------------------------------
_LIBS_DIR = Path(__file__).resolve().parent / "libs"
_hackrf_ready = False


def _ensure_hackrf_libs() -> None:
    """Register bundled DLL directory and fix pyhackrf2 library name."""
    global _hackrf_ready
    if _hackrf_ready or sys.platform != "win32":
        return
    _hackrf_ready = True

    # 1. Register our bundled libs/ so LoadLibrary can find hackrf.dll
    if _LIBS_DIR.is_dir():
        os.add_dll_directory(str(_LIBS_DIR))
        log.debug("Registered DLL search dir: %s", _LIBS_DIR)

    # 2. If cinterface is already imported, nothing more to do
    if "pyhackrf2.cinterface" in sys.modules:
        return

    # 3. Patch ctypes.CDLL so the Linux name "libhackrf.so.0" becomes
    #    "hackrf.dll" when cinterface is first imported.
    import ctypes
    _OrigCDLL = ctypes.CDLL

    class _WinCDLL(_OrigCDLL):                          # type: ignore[misc]
        def __init__(self, name, *a, **kw):
            if name == "libhackrf.so.0":
                name = "hackrf.dll"
            super().__init__(name, *a, **kw)

    ctypes.CDLL = _WinCDLL                              # type: ignore[misc]
    try:
        import pyhackrf2.cinterface                     # noqa: F401
    finally:
        ctypes.CDLL = _OrigCDLL                         # restore


class HackRFDevice:
    """Wrapper around HackRF One with resource management.

    Requires the ``pyhackrf2`` package and HackRF drivers/firmware installed.
    Gain mapping: the single 0-50 gain slider is mapped to HackRF's
    LNA gain (0-40 dB, steps of 8) and VGA gain (0-62 dB, steps of 2).
    """

    FREQ_MIN_HZ = 1e6
    FREQ_MAX_HZ = 6e9
    GAIN_MAX = 50.0

    def __init__(self, device_index: int = 0) -> None:
        self._device_index = device_index
        self._dev = None
        self._last_config_key: Optional[tuple] = None
        self._streaming = False

    # ── Lifecycle ────────────────────────────────────────

    def open(self) -> None:
        if self._dev is None:
            _ensure_hackrf_libs()
            from pyhackrf2 import HackRF
            self._dev = HackRF(device_index=self._device_index)
            self._last_config_key = None

    def close(self) -> None:
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass
            # pyhackrf2 bug: close() sets self.device_opened instead of
            # self._device_opened, so __del__ tries to close again.
            # Prevent the access-violation spam by marking it ourselves.
            self._dev._device_opened = False
            self._dev = None
            self._last_config_key = None

    def __enter__(self) -> "HackRFDevice":
        self.open()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ── Gain mapping ────────────────────────────────────

    @staticmethod
    def _map_gain(gain: float) -> tuple[int, int]:
        """Map a 0-50 gain value to (lna_gain, vga_gain) for HackRF.

        LNA gain: 0-40 dB in steps of 8.
        VGA gain: 0-62 dB in steps of 2.
        """
        lna = round(min(gain * 40 / 50, 40) / 8) * 8
        vga = round(min(gain * 62 / 50, 62) / 2) * 2
        return int(lna), int(vga)

    # ── Configuration ───────────────────────────────────

    def _config_key(self, config: CaptureConfig) -> tuple:
        return (config.sample_rate, config.center_freq, config.gain, config.bias_tee)

    def _apply_config(self, config: CaptureConfig) -> None:
        """Apply device settings, reopening the device when config changes.

        pyhackrf2's ``read_samples`` performs a full start_rx/stop_rx cycle.
        After ``stop_rx`` the USB transfer pipeline may not be fully drained,
        causing a subsequent ``start_rx`` to hang.  Closing and reopening the
        device between captures avoids the stale-state issue entirely — the
        ~100 ms overhead per retune is negligible for scan workloads.
        """
        if self._dev is None:
            raise RuntimeError("HackRF not open. Use 'with create_device(\"hackrf\") as sdr:'")

        config_key = self._config_key(config)
        if config_key == self._last_config_key:
            return

        # Reopen device to reset USB transfer state
        if self._last_config_key is not None:
            from pyhackrf2 import HackRF
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev._device_opened = False  # prevent __del__ double-close
            self._dev = HackRF(device_index=self._device_index)

        sample_rate = max(config.sample_rate, _MIN_SAMPLE_RATE)
        lna, vga = self._map_gain(config.gain)

        try:
            self._dev.sample_rate = sample_rate
            self._dev.center_freq = config.center_freq
            self._dev.lna_gain = lna
            self._dev.vga_gain = vga
            if hasattr(self._dev, 'bias_tee_on'):
                self._dev.bias_tee_on = config.bias_tee
            elif config.bias_tee and hasattr(self._dev, 'set_antenna_enable'):
                self._dev.set_antenna_enable(True)
        except Exception as exc:
            self._last_config_key = None
            raise RuntimeError(
                f"HackRF config failed (freq={config.center_freq/1e6:.1f} MHz, "
                f"LNA={lna} dB, VGA={vga} dB): {exc}"
            ) from exc

        self._last_config_key = config_key

    # ── Capture (blocking) ──────────────────────────────

    def capture(self, config: CaptureConfig) -> CaptureResult:
        """Capture I/Q samples based on config."""
        self._apply_config(config)

        num_samples = int(config.sample_rate * config.duration)
        if num_samples > config.max_samples:
            num_samples = config.max_samples

        actual_duration = num_samples / config.sample_rate

        # Single read_samples() call — HackRF starts/stops RX internally
        # and does not handle repeated start/stop cycles well.
        try:
            samples = self._dev.read_samples(num_samples)
        except Exception:
            log.error("HackRF read failed for %d samples.", num_samples)
            raise

        return CaptureResult(
            samples=samples,
            config=config,
            actual_duration=actual_duration,
            num_samples=len(samples),
        )

    def quick_capture(
        self, freq_mhz: float, duration: float = 5.0, **kwargs
    ) -> CaptureResult:
        """Convenience method — capture by frequency in MHz."""
        config = CaptureConfig(center_freq=freq_mhz * 1e6, duration=duration, **kwargs)
        return self.capture(config)

    # ── Continuous streaming (live mode) ─────────────────

    def configure(self, config: CaptureConfig) -> None:
        """Apply device settings without reading data."""
        if self._dev is None:
            raise RuntimeError("HackRF not open")

        sample_rate = max(config.sample_rate, _MIN_SAMPLE_RATE)
        lna, vga = self._map_gain(config.gain)

        try:
            self._dev.sample_rate = sample_rate
            self._dev.center_freq = config.center_freq
            self._dev.lna_gain = lna
            self._dev.vga_gain = vga
            if hasattr(self._dev, 'bias_tee_on'):
                self._dev.bias_tee_on = config.bias_tee
            elif config.bias_tee and hasattr(self._dev, 'set_antenna_enable'):
                self._dev.set_antenna_enable(True)
        except Exception as exc:
            raise RuntimeError(
                f"HackRF configure failed (freq={config.center_freq/1e6:.1f} MHz, "
                f"LNA={lna} dB, VGA={vga} dB): {exc}"
            ) from exc

        self._last_config_key = self._config_key(config)

    def start_stream(self, callback: Callable[[np.ndarray], None],
                     num_samples: int) -> None:
        """Start continuous RX streaming. Blocks until stop_stream().

        Uses pyhackrf2's ``start_rx`` with a pipe function so a single
        RX session stays open for the entire live duration.  Raw I/Q bytes
        are accumulated and delivered as complex-float numpy chunks of
        *num_samples* via *callback*.
        """
        if self._dev is None:
            raise RuntimeError("HackRF not open")

        self._streaming = True
        # 2 bytes per sample (I + Q as int8)
        target_bytes = num_samples * 2
        buf = bytearray()

        def _pipe(raw_bytes: bytes) -> bool:
            """Called from the C callback thread with each USB transfer."""
            nonlocal buf
            if not self._streaming:
                return True  # signal stop

            buf += raw_bytes
            while len(buf) >= target_bytes:
                chunk = buf[:target_bytes]
                buf = buf[target_bytes:]
                values = np.frombuffer(chunk, dtype=np.int8)
                iq = values.astype(np.float64).view(np.complex128)
                iq /= 127.5
                iq -= (1 + 1j)
                callback(iq)
                if not self._streaming:
                    return True
            return False

        self._dev._sample_count_limit = 0  # unlimited
        self._dev.start_rx(pipe_function=_pipe)

        # start_rx returns immediately; block here until streaming stops
        from pyhackrf2 import TransceiverMode
        while (self._streaming and
               self._dev._transceiver_mode != TransceiverMode.HACKRF_TRANSCEIVER_MODE_OFF):
            import time
            time.sleep(0.01)

        try:
            self._dev.stop_rx()
        except Exception:
            pass

    def retune(self, center_freq: float, gain: float) -> None:
        """Change center freq and gain while streaming. Thread-safe."""
        if self._dev is None:
            raise RuntimeError("HackRF not open")
        lna, vga = self._map_gain(gain)
        try:
            self._dev.center_freq = center_freq
            self._dev.lna_gain = lna
            self._dev.vga_gain = vga
        except Exception as exc:
            log.error("HackRF retune failed at %.1f MHz: %s", center_freq / 1e6, exc)
            self._last_config_key = None
            raise RuntimeError(
                f"HackRF retune failed (freq={center_freq/1e6:.1f} MHz, "
                f"LNA={lna} dB, VGA={vga} dB): {exc}"
            ) from exc
        if self._last_config_key:
            self._last_config_key = (
                self._last_config_key[0], center_freq, gain, self._last_config_key[3],
            )

    def stop_stream(self) -> None:
        """Stop streaming, unblocking start_stream(). Thread-safe."""
        self._streaming = False
