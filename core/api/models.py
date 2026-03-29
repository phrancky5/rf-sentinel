"""Pydantic models for the RFSentinel API."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from core.dsp.types import DemodMode


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


class ScanRequest(BaseModel):
    """Request to start a spectrum + waterfall scan over a frequency range."""
    start_mhz: float = Field(85.0, ge=1.0, le=6000.0)
    stop_mhz: float = Field(140.0, ge=1.0, le=6000.0)
    duration: float = Field(5.0, ge=0.5, le=30.0)
    gain: float = Field(30.0, ge=0.0, le=62.0)
    bias_tee: bool = Field(False, description="Enable bias-T supply for active antenna LNA")
    preset_band: Optional[str] = Field(None, max_length=80, description="Matched preset label for this scan")
    device: str = Field("rtlsdr", description="SDR driver: rtlsdr or hackrf")
    device_index: int = Field(0, ge=0, description="Device index when multiple devices of the same type are attached")


class LiveRequest(BaseModel):
    """Request to start live spectrum monitoring."""
    start_mhz: float = Field(97.0, ge=1.0, le=6000.0)
    stop_mhz: float = Field(99.0, ge=1.0, le=6000.0)
    gain: float = Field(30.0, ge=0.0, le=62.0)
    audio_enabled: bool = Field(False, description="Enable audio demodulation")
    demod_mode: DemodMode = Field(DemodMode.FM, description="Demodulation mode: fm or am")
    bias_tee: bool = Field(False, description="Enable bias-T supply for active antenna LNA")
    device: str = Field("rtlsdr", description="SDR driver: rtlsdr or hackrf")
    device_index: int = Field(0, ge=0, description="Device index when multiple devices of the same type are attached")


class RetuneRequest(BaseModel):
    """Retune live stream without restart."""
    start_mhz: float = Field(97.0, ge=1.0, le=6000.0)
    stop_mhz: float = Field(99.0, ge=1.0, le=6000.0)
    gain: float = Field(30.0, ge=0.0, le=62.0)


class AudioToggleRequest(BaseModel):
    """Toggle audio demod while live is running."""
    enabled: bool = Field(..., description="Enable or disable audio")
    demod_mode: DemodMode = Field(DemodMode.FM, description="Demodulation mode: fm or am")


class VfoRequest(BaseModel):
    """Set VFO frequency within the captured bandwidth."""
    freq_mhz: float = Field(..., ge=1.0, le=6000.0, description="VFO frequency in MHz")


class JobInfo(BaseModel):
    """Job status response."""
    id: str
    type: str
    status: JobStatus
    params: dict
    error: Optional[str] = None
    created_at: str
    duration_s: Optional[float] = None


class ScanNoteUpdateRequest(BaseModel):
    """Editable note attached to a completed scan."""
    note: str = Field("", max_length=2000)


class SavedFrequencyCreateRequest(BaseModel):
    """Create a saved frequency bookmark."""
    freq_mhz: float = Field(..., ge=1.0, le=6000.0)
    description: str = Field(..., min_length=1, max_length=240)
    scan_id: Optional[str] = Field(None, max_length=64)
    preset_band: Optional[str] = Field(None, max_length=80)
