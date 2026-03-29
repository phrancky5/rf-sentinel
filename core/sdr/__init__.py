"""SDR device interface — capture I/Q samples from supported SDR hardware.

Supported devices:
  - rtlsdr  — RTL-SDR (pyrtlsdr)
  - hackrf  — HackRF One (pyhackrf2)

Use ``create_device(driver)`` or the backward-compatible ``SDRDevice(driver)``
factory to obtain a device instance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)


@dataclass
class CaptureConfig:
    """Configuration for an SDR capture session."""

    center_freq: float  # Hz
    sample_rate: float = 1.024e6  # Hz
    gain: float = 30.0  # dB
    duration: float = 5.0  # seconds
    bias_tee: bool = False  # Enable bias-T to power active antennas
    max_samples: int = 128 * 1024 * 1024  # ~1 GB limit (128M complex64 samples)


@dataclass
class CaptureResult:
    """Result of a capture session with metadata."""

    samples: np.ndarray
    config: CaptureConfig
    actual_duration: float  # seconds
    num_samples: int


def create_device(device_type: str = "rtlsdr", device_index: int = 0):
    """Factory — create an SDR device instance by driver name.

    Args:
        device_type: ``"rtlsdr"`` (default) or ``"hackrf"``.
        device_index: Zero-based index when multiple devices of the same
            type are connected.

    Returns:
        A device object with open/close/capture/start_stream/retune/stop_stream
        methods + context-manager support.
    """
    if device_type == "hackrf":
        from core.sdr.hackrf_device import HackRFDevice
        return HackRFDevice(device_index=device_index)
    from core.sdr.rtlsdr_device import RtlSdrDevice
    return RtlSdrDevice(device_index=device_index)


def enumerate_devices() -> list[dict]:
    """Return a list of all attached SDR devices.

    Each entry: ``{"type": str, "index": int, "label": str, "serial": str}``.
    The ``index`` is the per-driver device index (pass to ``create_device``).
    """
    devices: list[dict] = []

    # ── RTL-SDR ──
    try:
        import ctypes
        from rtlsdr import librtlsdr

        n = librtlsdr.rtlsdr_get_device_count()
        for i in range(n):
            name_raw = librtlsdr.rtlsdr_get_device_name(i)
            name = name_raw.decode() if isinstance(name_raw, bytes) else str(name_raw)
            serial = ""
            try:
                manuf = (ctypes.c_ubyte * 256)()
                product = (ctypes.c_ubyte * 256)()
                ser_buf = (ctypes.c_ubyte * 256)()
                librtlsdr.rtlsdr_get_device_usb_strings(i, manuf, product, ser_buf)
                serial = bytes(ser_buf).split(b"\x00")[0].decode(errors="replace")
            except Exception:
                pass
            label = f"{name} #{i}" if n > 1 else name
            if serial:
                label += f" [{serial[-8:]}]"
            devices.append({
                "type": "rtlsdr", "index": i,
                "label": label, "serial": serial,
            })
    except Exception as exc:
        log.debug("RTL-SDR enumeration failed: %s", exc)

    # ── HackRF ──
    try:
        from core.sdr.hackrf_device import _ensure_hackrf_libs
        _ensure_hackrf_libs()
        from pyhackrf2 import HackRF

        serials = HackRF.enumerate()
        for i, ser in enumerate(serials):
            label = f"HackRF One #{i}" if len(serials) > 1 else "HackRF One"
            if ser:
                label += f" [{ser[-8:]}]"
            devices.append({
                "type": "hackrf", "index": i,
                "label": label, "serial": ser,
            })
    except Exception as exc:
        log.debug("HackRF enumeration failed: %s", exc)

    return devices


# Backward compat — SDRDevice() still returns an RTL-SDR device by default.
SDRDevice = create_device
