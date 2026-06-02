"""门禁系统后端：FastAPI 入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import settings
from app.db import get_engine, seed_admin_user
from app.routers import admin, auth, door, logs, visitor, voiceprint

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()
    seed_admin_user()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    yield


def _parse_cors(origins: str) -> list[str]:
    o = origins.strip()
    if o == "*":
        return ["*"]
    return [x.strip() for x in o.split(",") if x.strip()]


app = FastAPI(title="voice-door-backend", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    msg = detail if isinstance(detail, str) else str(detail)
    return JSONResponse(status_code=exc.status_code, content={"message": msg})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errs = exc.errors()
    first = errs[0] if errs else {}
    loc = ".".join(str(x) for x in first.get("loc", ()))
    msg = first.get("msg", "参数校验失败")
    return JSONResponse(
        status_code=422,
        content={"message": f"{loc}: {msg}" if loc else msg},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"message": "服务器内部错误"},
    )


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "voice-door-backend", "version": __version__}


api_prefix = "/api"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(door.router, prefix=api_prefix)
app.include_router(voiceprint.router, prefix=api_prefix)
app.include_router(visitor.router, prefix=api_prefix)
app.include_router(logs.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)
