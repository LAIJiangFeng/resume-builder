# author: jf
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DOTENV_LOADED = False


def _load_local_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    # python-ai-backend/.env 是手写的轻量加载器，不依赖 python-dotenv。
    env_file = Path(__file__).resolve().parents[3] / ".env"
    if not env_file.exists():
        _DOTENV_LOADED = True
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())

    _DOTENV_LOADED = True


def _get_int(name: str, default: int) -> int:
    # 环境变量常常是字符串，这里统一做安全整数转换。
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    # 超时参数允许用浮点数（例如 2.5 秒）。
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_first_non_empty(*names: str, default: str = "") -> str:
    # 支持“专用变量优先，通用变量兜底”的读取顺序。
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    # 这里只保留当前 Python 后端实际会用到的配置项。
    server_port: int
    app_cors_allowed_origins: str
    auth_token_secret: str
    auth_token_ttl_seconds: int
    app_rag_top_k: int
    app_interview_rag_top_k: int
    app_interview_rag_similarity_threshold: float
    app_interview_rag_timeout_seconds: float
    embedding_provider: str
    embedding_model_name: str
    embedding_base_url: str
    embedding_timeout_seconds: float
    openai_base_url: str
    openai_api_key: str
    openai_chat_model: str
    openai_chat_completions_path: str
    openai_chat_timeout_seconds: float
    openai_embedding_base_url: str
    openai_embedding_api_key: str
    openai_embedding_model: str
    openai_embedding_timeout_seconds: float
    ollama_embedding_base_url: str
    ollama_embedding_model: str
    ollama_embedding_timeout_seconds: float
    openai_vision_model: str
    openai_vision_detail: str
    openai_vision_base_url: str
    openai_vision_api_key: str
    openai_vision_timeout_seconds: float
    openai_realtime_base_url: str
    openai_realtime_api_key: str
    openai_realtime_client_secrets_path: str
    openai_realtime_calls_path: str
    openai_realtime_transcription_model: str
    openai_realtime_language: str
    mysql_datasource_url: str
    mysql_datasource_username: str
    mysql_datasource_password: str
    pgvector_datasource_url: str
    pgvector_datasource_username: str
    pgvector_datasource_password: str
    pgvector_connect_timeout_seconds: int
    rag_chunk_size: int
    rag_chunk_overlap: int
    rag_max_file_size_mb: int
    autogen_enabled: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_local_dotenv()
    # chat 场景优先使用专用 base_url/api_key，没有时退回通用 OPENAI_*。
    openai_base_url = _get_first_non_empty("OPENAI_CHAT_BASE_URL", "OPENAI_BASE_URL", default="https://api.openai.com")
    openai_api_key = _get_first_non_empty("OPENAI_CHAT_API_KEY", "OPENAI_API_KEY")
    # embedding 允许单独走兼容 OpenAI 的第三方路由。
    openai_embedding_base_url = _get_first_non_empty(
        "OPENAI_EMBEDDING_BASE_URL",
        "OPENAI_CHAT_BASE_URL",
        "OPENAI_BASE_URL",
        default=openai_base_url,
    )
    openai_embedding_api_key = _get_first_non_empty(
        "OPENAI_EMBEDDING_API_KEY",
        "OPENAI_CHAT_API_KEY",
        "OPENAI_API_KEY",
        default=openai_api_key,
    )
    # embedding 支持按 provider 切换：openai（默认）或 ollama。
    embedding_provider = _normalize_embedding_provider(os.getenv("EMBEDDING_PROVIDER", "openai"))
    ollama_embedding_base_url = _get_first_non_empty(
        "OLLAMA_EMBEDDING_BASE_URL",
        "OLLAMA_BASE_URL",
        default="http://127.0.0.1:11434",
    )
    ollama_embedding_model = (os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text") or "").strip() or "nomic-embed-text"
    ollama_embedding_timeout_seconds = max(1.0, _get_float("OLLAMA_EMBEDDING_TIMEOUT_SECONDS", 45.0))
    openai_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_embedding_timeout_seconds = max(1.0, _get_float("OPENAI_EMBEDDING_TIMEOUT_SECONDS", 45.0))

    # 统一导出当前生效的 embedding 元信息，供容器装配和日志复用。
    if embedding_provider == "ollama":
        embedding_model_name = ollama_embedding_model
        embedding_base_url = ollama_embedding_base_url
        embedding_timeout_seconds = ollama_embedding_timeout_seconds
    else:
        embedding_model_name = openai_embedding_model
        embedding_base_url = openai_embedding_base_url
        embedding_timeout_seconds = openai_embedding_timeout_seconds

    return Settings(
        server_port=_get_int("SERVER_PORT", 8999),
        app_cors_allowed_origins=os.getenv(
            "APP_CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ),
        auth_token_secret=os.getenv("APP_AUTH_TOKEN_SECRET", "resume-builder-local-demo-auth-secret"),
        auth_token_ttl_seconds=max(300, _get_int("APP_AUTH_TOKEN_TTL_SECONDS", 43_200)),
        app_rag_top_k=_get_int("APP_RAG_TOP_K", 5),
        app_interview_rag_top_k=max(1, _get_int("APP_INTERVIEW_RAG_TOP_K", _get_int("APP_RAG_TOP_K", 5))),
        app_interview_rag_similarity_threshold=_normalize_similarity_threshold(
            _get_float("APP_INTERVIEW_RAG_SIMILARITY_THRESHOLD", 0.0)
        ),
        app_interview_rag_timeout_seconds=max(0.2, _get_float("APP_INTERVIEW_RAG_TIMEOUT_SECONDS", 3.0)),
        embedding_provider=embedding_provider,
        embedding_model_name=embedding_model_name,
        embedding_base_url=embedding_base_url,
        embedding_timeout_seconds=embedding_timeout_seconds,
        openai_base_url=openai_base_url,
        openai_api_key=openai_api_key,
        openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4"),
        openai_chat_completions_path=os.getenv("OPENAI_CHAT_COMPLETIONS_PATH", "/v1/chat/completions"),
        openai_chat_timeout_seconds=max(3.0, _get_float("OPENAI_CHAT_TIMEOUT_SECONDS", 25.0)),
        openai_embedding_base_url=openai_embedding_base_url,
        openai_embedding_api_key=openai_embedding_api_key,
        openai_embedding_model=openai_embedding_model,
        openai_embedding_timeout_seconds=openai_embedding_timeout_seconds,
        ollama_embedding_base_url=ollama_embedding_base_url,
        ollama_embedding_model=ollama_embedding_model,
        ollama_embedding_timeout_seconds=ollama_embedding_timeout_seconds,
        openai_vision_model=os.getenv("OPENAI_VISION_MODEL", "gpt-4.1"),
        openai_vision_detail=os.getenv("OPENAI_VISION_DETAIL", "high"),
        openai_vision_base_url=_get_first_non_empty("OPENAI_VISION_BASE_URL", "OPENAI_CHAT_BASE_URL", "OPENAI_BASE_URL", default=openai_base_url),
        openai_vision_api_key=_get_first_non_empty("OPENAI_VISION_API_KEY", "OPENAI_CHAT_API_KEY", "OPENAI_API_KEY", default=openai_api_key),
        openai_vision_timeout_seconds=max(3.0, _get_float("OPENAI_VISION_TIMEOUT_SECONDS", 40.0)),
        openai_realtime_base_url=_get_first_non_empty("OPENAI_REALTIME_BASE_URL", "OPENAI_BASE_URL", default=openai_base_url),
        openai_realtime_api_key=_get_first_non_empty("OPENAI_REALTIME_API_KEY", "OPENAI_API_KEY", default=openai_api_key),
        openai_realtime_client_secrets_path=os.getenv("OPENAI_REALTIME_CLIENT_SECRETS_PATH", "/v1/realtime/client_secrets"),
        openai_realtime_calls_path=os.getenv("OPENAI_REALTIME_CALLS_PATH", "/v1/realtime/calls"),
        openai_realtime_transcription_model=os.getenv("OPENAI_REALTIME_TRANSCRIPTION_MODEL", "gpt-4o-transcribe"),
        openai_realtime_language=os.getenv("OPENAI_REALTIME_LANGUAGE", "zh"),
        mysql_datasource_url=os.getenv("MYSQL_DATASOURCE_URL", ""),
        mysql_datasource_username=os.getenv("MYSQL_DATASOURCE_USERNAME", ""),
        mysql_datasource_password=os.getenv("MYSQL_DATASOURCE_PASSWORD", ""),
        pgvector_datasource_url=os.getenv("PGVECTOR_DATASOURCE_URL", ""),
        pgvector_datasource_username=os.getenv("PGVECTOR_DATASOURCE_USERNAME", ""),
        pgvector_datasource_password=os.getenv("PGVECTOR_DATASOURCE_PASSWORD", ""),
        pgvector_connect_timeout_seconds=max(1, _get_int("PGVECTOR_CONNECT_TIMEOUT_SECONDS", 8)),
        rag_chunk_size=_get_int("RAG_CHUNK_SIZE", 1200),
        rag_chunk_overlap=_get_int("RAG_CHUNK_OVERLAP", 200),
        rag_max_file_size_mb=_get_int("RAG_MAX_FILE_SIZE_MB", 10),
        autogen_enabled=os.getenv("AUTOGEN_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
    )


def _normalize_embedding_provider(raw_provider: str | None) -> str:
    provider = (raw_provider or "").strip().lower()
    if provider in {"openai", "ollama"}:
        return provider
    return "openai"


def _normalize_similarity_threshold(raw_value: float) -> float:
    try:
        threshold = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    if threshold < 0.0:
        return 0.0
    if threshold > 1.0:
        return 1.0
    return threshold
