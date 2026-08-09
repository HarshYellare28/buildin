"""DAWA API — system of record for plans, doses, policy, events, packets.

Run:
    uvicorn src.main:app --reload --port 8000   (from services/api)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db
from .config import CORS_ORIGINS, EXTRACT_MODE, LOG_LEVEL
from .errors import ApiError
from .routes import demo, doses, events, health, packets, people, plans, policy
from .services import sarvam
from .services.seed import ensure_seeded


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    ensure_seeded()
    yield


def create_app() -> FastAPI:
    # uvicorn only configures its own loggers, so without this every log line
    # from src/** is dropped and Sarvam failures stay invisible.
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger(__name__).info(
        "DAWA API starting: extract_mode=%s sarvam_key=%s",
        EXTRACT_MODE,
        "set" if sarvam.is_configured() else "MISSING",
    )

    app = FastAPI(title="DAWA API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (health, people, plans, doses, events, packets, policy, demo):
        app.include_router(module.router)

    @app.exception_handler(ApiError)
    def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.body())

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "; ".join(
                        f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}"
                        for e in exc.errors()
                    )
                    or "Invalid request body",
                }
            },
        )

    return app


app = create_app()
