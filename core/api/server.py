"""RFSentinel Web UI — FastAPI app setup and entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api import ws
from core.api.routes import create_routes
from core.api.runner import JobRunner

logger = logging.getLogger("rfsentinel.server")

# ── App setup ───────────────────────────────────────────

runner = JobRunner(
    log_cb=ws.log_callback,
    audio_cb=ws.audio_callback,
    job_status_cb=ws.job_status_callback,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.api.db import init as init_db
    init_db()
    ws.set_loop(asyncio.get_running_loop())
    logger.info("RFSentinel server started (audio support enabled)")
    yield
    runner.live.stop()
    runner._pool.shutdown(wait=False)
    logger.info("RFSentinel server stopped")


app = FastAPI(
    title="RFSentinel",
    description="RF Spectrum Monitoring & Classification",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws.router)
app.include_router(create_routes(runner))


# ── Entry point ─────────────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 8900) -> None:
    import uvicorn

    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║     RFSentinel — UI Server           ║")
    print(f"  ║     http://{host}:{port}            ║")
    print(f"  ╚══════════════════════════════════════╝\n")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8900)
    args = parser.parse_args()
    run_server(port=args.port)
