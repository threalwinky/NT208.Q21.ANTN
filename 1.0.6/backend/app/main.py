from __future__ import annotations

import logging
import logging.config
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import get_settings, validate_runtime_config
from app.core.rate_limit import limiter
from app.db.init_db import init_db

settings = get_settings()

_LOG_LEVEL = logging.DEBUG if settings.app_env == "development" else logging.INFO

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "level": _LOG_LEVEL,
        "handlers": ["console"],
    },
    "loggers": {
        "uvicorn": {"propagate": True},
        "uvicorn.access": {"propagate": True},
        "sqlalchemy.engine": {
            "level": logging.WARNING,
            "propagate": True,
        },
    },
})

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_config(settings)
    init_db()
    logger.info("Studify v%s khởi động (%s)", settings.app_version, settings.app_env)
    yield
    logger.info("Studify đã tắt.")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict:
    return {
        "name": "Studify",
        "version": settings.app_version,
        "description": "Student companion platform for UIT students",
    }


@app.get("/health")
def root_health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
