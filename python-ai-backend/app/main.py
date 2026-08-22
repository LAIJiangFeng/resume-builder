# author: jf
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# 应用入口需要最早统一 stdout/stderr 的编码。
# Windows 下如果保留默认 gbk，AI 面试链路里的 uvicorn/error 日志在被外层按 UTF-8 收集时，
# 会把类似 “[AI面试][RAG检索]” 的中文前缀打成 “闈㈣瘯” 这类乱码。
# 这里在导入业务模块前重配标准流，保证 print 和 logging 两条链路都输出 UTF-8。
def _configure_stdio_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            continue


_configure_stdio_encoding()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import ALL_ROUTERS
from app.api.errors.handlers import register_error_handlers
from app.infrastructure.config.settings import get_settings

settings = get_settings()
app = FastAPI(title="python-ai-backend", version="0.1.0")
BOOT_TIME = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.app_cors_allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "UP"}


@app.get("/health/runtime")
def health_runtime(request: Request) -> dict[str, str | int]:
    return {
        "status": "UP",
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
        "pythonExecutable": sys.executable,
        "appFile": str(Path(__file__).resolve()),
        "configuredPort": settings.server_port,
        "requestPort": request.url.port or settings.server_port,
        "bootTime": BOOT_TIME,
    }


register_error_handlers(app)

for route in ALL_ROUTERS:
    app.include_router(route)
