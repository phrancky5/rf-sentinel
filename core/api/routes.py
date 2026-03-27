"""REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.api.models import (
    ScanRequest, LiveRequest, RetuneRequest, AudioToggleRequest, VfoRequest,
    ScanNoteUpdateRequest, SavedFrequencyCreateRequest,
)
from core.api.runner import JobRunner
from core.api.db import (
    list_scans, get_scan, delete_scan as db_delete, get_settings, save_settings,
    update_scan_note, list_saved_frequencies, save_frequency, delete_saved_frequency,
)


def create_routes(runner: JobRunner) -> APIRouter:
    router = APIRouter()

    @router.get("/api/status")
    async def get_status():
        return {"status": "online"}

    @router.post("/api/scan")
    async def start_scan(req: ScanRequest):
        job = runner.submit_scan(
            req.start_mhz, req.stop_mhz, req.duration, req.gain,
            req.bias_tee, req.preset_band,
        )
        return {"job_id": job.id, "status": job.status.value}

    @router.post("/api/live/start")
    async def start_live(req: LiveRequest):
        runner.live.start(req.start_mhz, req.stop_mhz, req.gain,
                          req.audio_enabled, req.demod_mode, req.bias_tee)
        return {"status": "started", "start_mhz": req.start_mhz, "stop_mhz": req.stop_mhz,
                "audio_enabled": req.audio_enabled, "demod_mode": req.demod_mode}

    @router.post("/api/live/stop")
    async def stop_live():
        runner.live.stop()
        return {"status": "stopped"}

    @router.post("/api/live/retune")
    async def retune_live(req: RetuneRequest):
        if not runner.live.active:
            return JSONResponse({"error": "Live mode is not active"}, status_code=400)
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, runner.live.retune, req.start_mhz, req.stop_mhz, req.gain)
        return {"status": "retuned", "start_mhz": req.start_mhz, "stop_mhz": req.stop_mhz}

    @router.post("/api/live/audio")
    async def toggle_audio(req: AudioToggleRequest):
        if not runner.live.active:
            return JSONResponse({"error": "Live mode is not active"}, status_code=400)
        runner.live.toggle_audio(req.enabled, req.demod_mode)
        return {"audio_enabled": req.enabled, "demod_mode": req.demod_mode}

    @router.post("/api/live/vfo")
    async def set_vfo(req: VfoRequest):
        if not runner.live.active:
            return JSONResponse({"error": "Live mode is not active"}, status_code=400)
        runner.live.set_vfo(req.freq_mhz)
        return {"vfo_freq_mhz": req.freq_mhz}

    @router.post("/api/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str):
        if runner.cancel_job(job_id):
            return {"status": "cancelled"}
        return JSONResponse({"error": "Job not found or not cancellable"}, status_code=404)

    @router.get("/api/scans")
    async def get_scan_history(limit: int = 50, offset: int = 0):
        return list_scans(limit, offset)

    @router.get("/api/scans/{scan_id}")
    async def get_scan_detail(scan_id: str):
        result = get_scan(scan_id)
        if not result:
            return JSONResponse({"error": "Scan not found"}, status_code=404)
        return result

    @router.delete("/api/scans/{scan_id}")
    async def delete_scan(scan_id: str):
        runner.jobs.pop(scan_id, None)
        if db_delete(scan_id):
            return {"status": "deleted"}
        return JSONResponse({"error": "Scan not found"}, status_code=404)

    @router.post("/api/scans/{scan_id}/note")
    async def update_scan_note_route(scan_id: str, req: ScanNoteUpdateRequest):
        result = update_scan_note(scan_id, req.note)
        if not result:
            return JSONResponse({"error": "Scan not found"}, status_code=404)
        return result

    @router.get("/api/frequencies")
    async def get_saved_frequencies(limit: int = 200):
        return {"items": list_saved_frequencies(limit)}

    @router.post("/api/frequencies")
    async def create_saved_frequency(req: SavedFrequencyCreateRequest):
        item = save_frequency(req.freq_mhz, req.description, req.scan_id, req.preset_band)
        if not item:
            return JSONResponse({"error": "Unable to save frequency"}, status_code=500)
        return item

    @router.delete("/api/frequencies/{freq_id}")
    async def remove_saved_frequency(freq_id: int):
        if delete_saved_frequency(freq_id):
            return {"status": "deleted"}
        return JSONResponse({"error": "Saved frequency not found"}, status_code=404)

    # ── Settings ─────────────────────────────────────────────────────────

    @router.get("/api/settings")
    async def fetch_settings():
        return get_settings()

    @router.post("/api/settings")
    async def update_settings(payload: dict):
        save_settings(payload)
        return {"status": "saved"}

    return router
