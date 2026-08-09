"""Standalone app for developing the voice module before Barkha's API exists.

    cd services/api/src && uvicorn voice.dev_app:app --reload --port 8100

This is a harness, not the product server. When the real app exists it mounts voice.router
directly and this file stops being used.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .router import router

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="DAWA voice (dev harness)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def mic_page() -> FileResponse:
    return FileResponse(STATIC / "mic.html")
