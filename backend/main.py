"""
TradiQ — FastAPI Application Entry Point
Starts the API server and Sunday scheduler together.
"""

import logging
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ is on the path
sys.path.insert(0, os.path.dirname(__file__))

from api.routes import router
from scheduler.sunday_job import create_scheduler

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tradiq")

# ── Scheduler lifecycle ───────────────────────────────────────────────────────
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    logger.info("🤖 TradiQ starting up...")
    _scheduler = create_scheduler()
    _scheduler.start()
    logger.info("⏰ Scheduler started — 4 jobs active:")
    logger.info("   💓 Keep-alive ping       every 10 minutes")
    logger.info("   🌙 Nightly batched scan  2:00 AM IST Mon–Sat")
    logger.info("   🔭 Saturday deep scan    11:00 PM IST Saturday")
    logger.info("   📋 Sunday weekly report  9:00 AM IST Sunday")
    yield
    logger.info("🛑 TradiQ shutting down...")
    if _scheduler:
        _scheduler.shutdown(wait=False)


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="TradiQ — Indian Stock AI Bot",
    description="AI-powered Indian stock market recommendations. Every Sunday, top 15 picks.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the React frontend to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "TradiQ",
        "status": "running",
        "docs": "/docs",
        "picks": "/api/picks/latest",
        "trigger": "POST /api/run",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
