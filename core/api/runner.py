"""Background job runner — executes SDR tasks in threads and streams logs."""

from __future__ import annotations

import threading
import time
import uuid
import logging
import traceback
from datetime import datetime, timezone
from typing import Callable, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from core.api.models import JobStatus
from core.api.live import LiveSession
from core.api.db import save_scan
import numpy as np

logger = logging.getLogger("rfsentinel.runner")

SCAN_WF_MAX_FREQ_BINS = 1024
SCAN_WF_MAX_TIME_BINS = 256


class CancelledError(Exception):
    pass


@dataclass
class Job:
    id: str
    type: str
    status: JobStatus
    params: dict
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    duration_s: Optional[float] = None
    cancel: threading.Event = field(default_factory=threading.Event)


class JobRunner:
    """Manages background SDR jobs."""

    def __init__(self, log_cb: Callable[[str, str], None],
                 audio_cb: Callable[[bytes], None],
                 job_status_cb: Callable[[dict], None]) -> None:
        self._log_cb = log_cb
        self._audio_cb = audio_cb
        self._job_status_cb = job_status_cb
        self.jobs: dict[str, Job] = {}
        self._pool = ThreadPoolExecutor(max_workers=1)
        self.live = LiveSession(emit=self._emit, emit_audio=self._emit_audio)
        self._current_sdr = None

    def _emit(self, job_id: str, msg: str) -> None:
        if job_id != "__spectrum__":
            logger.info(f"[{job_id[:8]}] {msg}")
        self._log_cb(job_id, msg)

    def _emit_audio(self, pcm_bytes: bytes) -> None:
        self._audio_cb(pcm_bytes)

    def _emit_job_status(self, job: Job) -> None:
        self._job_status_cb({
            "id": job.id,
            "type": job.type,
            "status": job.status.value,
            "params": job.params,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "duration_s": job.duration_s,
        })

    def _submit_job(self, job_type: str, params: dict, run_fn: Callable) -> Job:
        if self.live.active:
            self.live.stop()
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, type=job_type, status=JobStatus.PENDING, params=params)
        self.jobs[job_id] = job
        self._emit_job_status(job)
        self._pool.submit(run_fn, job)
        return job

    def submit_scan(self, start_mhz: float, stop_mhz: float,
                    duration: float, gain: float, bias_tee: bool = False,
                    preset_band: str | None = None) -> Job:
        return self._submit_job("scan", {
            "start_mhz": start_mhz, "stop_mhz": stop_mhz,
            "duration": duration, "gain": gain, "bias_tee": bias_tee,
            "preset_band": preset_band, "note": "",
        }, self._run_scan)

    # ── Shared helpers ──────────────────────────────────

    def _capture_segments(self, job: Job, label: str, compute_fn, trim_fn):
        """Capture I/Q across planned chunks, returning processed segments."""
        from core.dsp import plan_chunks, SAMPLE_RATE
        from core.sdr import SDRDevice, CaptureConfig

        p = job.params
        centers = plan_chunks(p["start_mhz"] * 1e6, p["stop_mhz"] * 1e6)
        num_chunks = len(centers)

        self._emit(job.id, f"{label}: {p['start_mhz']:.1f} – {p['stop_mhz']:.1f} MHz "
              f"({num_chunks} chunk{'s' if num_chunks > 1 else ''})")

        segments = []
        with SDRDevice() as sdr:
            self._current_sdr = sdr
            try:
                for i, fc in enumerate(centers):
                    if job.cancel.is_set():
                        raise CancelledError()
                    self._emit(job.id, f"  [{i+1}/{num_chunks}] Capturing {fc/1e6:.1f} MHz...")
                    config = CaptureConfig(
                        center_freq=fc, sample_rate=SAMPLE_RATE,
                        duration=p["duration"], gain=p["gain"],
                        bias_tee=p.get("bias_tee", False),
                    )
                    capture = sdr.capture(config)
                    data = compute_fn(capture)
                    if num_chunks > 1:
                        data = trim_fn(data)
                    segments.append(data)
            finally:
                self._current_sdr = None

        return segments, num_chunks

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
            return False
        job.cancel.set()
        if self._current_sdr:
            self._current_sdr.stop_stream()
        return True

    def _finalize_job(self, job: Job, t0: float) -> None:
        job.status = JobStatus.COMPLETE
        job.duration_s = round(time.time() - t0, 2)
        self._emit_job_status(job)
        save_scan(job)

    # ── Scan (stitched) ─────────────────────────────────

    def _run_scan(self, job: Job) -> None:
        job.status = JobStatus.RUNNING
        self._emit_job_status(job)
        t0 = time.time()

        try:
            from core.dsp import compute_waterfall, trim_waterfall, stitch_waterfalls

            segments, num_chunks = self._capture_segments(job, "Scan", compute_waterfall, trim_waterfall)
            if num_chunks > 1:
                self._emit(job.id, "  Note: chunks captured sequentially, not simultaneously")

            self._emit(job.id, "Stitching spectrum..." if num_chunks > 1 else "Processing...")
            result = stitch_waterfalls(segments)

            # 1D spectrum: send at full res (uPlot handles 25k+ points fine)
            spec_freqs = np.round(result.freqs_mhz, 4).tolist()
            spec_power = np.round(result.mean_psd_db, 1).tolist()

            # 2D waterfall: decimate more aggressively
            wf_freq_step = max(1, len(result.freqs_mhz) // SCAN_WF_MAX_FREQ_BINS)
            time_step = max(1, result.power_db.shape[1] // SCAN_WF_MAX_TIME_BINS)
            power_ds = result.power_db[::wf_freq_step, ::time_step]
            wf_freqs = np.round(result.freqs_mhz[::wf_freq_step], 4).tolist()

            job.params["waterfall_data"] = {
                "freqs_mhz": wf_freqs,
                "power_db": np.round(power_ds.T, 1).tolist(),
                "duration_s": round(float(result.times[-1]), 2),
            }
            job.params["spectrum_data"] = {
                "freqs_mhz": spec_freqs,
                "power_db": spec_power,
            }

            self._finalize_job(job, t0)
            self._emit(job.id, f"Scan complete ({job.duration_s}s)")

        except (CancelledError, Exception) as e:
            job.duration_s = round(time.time() - t0, 2)
            if isinstance(e, CancelledError) or job.cancel.is_set():
                job.status = JobStatus.CANCELLED
                self._emit(job.id, "Scan cancelled")
            else:
                job.status = JobStatus.ERROR
                job.error = str(e)
                self._emit(job.id, f"ERROR: {e}")
                logger.error(traceback.format_exc())
            self._emit_job_status(job)
        finally:
            import gc; gc.collect()
