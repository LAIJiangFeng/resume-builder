# author: jf
import logging
from urllib.parse import quote, urlsplit, urlunsplit

from app.application.ports.agent_runtime_port import AgentRuntimePort
from app.application.ports.auth_user_repository import AuthUserRepository
from app.application.ports.embedding_port import EmbeddingPort
from app.application.ports.file_parser_port import FileParserPort
from app.application.ports.image_markdown_ocr_port import ImageMarkdownOcrPort
from app.application.ports.interview_session_repository import InterviewSessionRepository
from app.application.ports.llm_port import ChatClientPort
from app.application.ports.resume_repository import ResumeRepository
from app.application.ports.vector_store_port import VectorStorePort
from app.application.services.auth_service import AuthService
from app.domain.services.document_chunking_service import DocumentChunkingService
from app.domain.services.interview_flow_service import InterviewGraph
from app.domain.services.logical_document_splitter_service import LogicalDocumentSplitterService
from app.domain.services.rag_retrieval_service import RagRetrieverService
from app.infrastructure.agents.autogen_runtime_adapter import AutoGenAgentRuntimeAdapter
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.factories.llm_factory import create_chat_client, create_realtime_client
from app.infrastructure.llm.openai_embedding_adapter import OpenAIEmbeddingAdapter
from app.infrastructure.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
from app.infrastructure.llm.openai_image_markdown_ocr_adapter import OpenAIImageMarkdownOcrAdapter
from app.infrastructure.mail.smtp_auth_mail_adapter import SmtpAuthMailAdapter
from app.infrastructure.persistence.mysql.auth_repository import MySqlAuthUserRepository
from app.infrastructure.persistence.mysql.resume_repository import MySqlResumeRepository
from app.infrastructure.persistence.mysql.session_repository import MySqlInterviewSessionRepository
from app.infrastructure.persistence.pgvector.vector_store_adapter import PgVectorStoreAdapter
from app.infrastructure.security.auth_security_adapter import AuthSecurityAdapter
from app.infrastructure.text.file_parser_adapter import FileParserAdapter

_LOGGER = logging.getLogger("uvicorn.error")


def resolve_settings() -> Settings:
    # 所有构建函数统一复用同一份 Settings，避免不同模块各自读取环境变量。
    return get_settings()


def build_chat_client(settings: Settings | None = None) -> ChatClientPort:
    return create_chat_client(settings)


def build_realtime_client(settings: Settings | None = None):
    return create_realtime_client(settings)


def _resolve_pgvector_connection_url(datasource_url: str, username: str, password: str) -> str:
    safe_url = (datasource_url or "").strip()
    if not safe_url:
        return ""

    # 兼容 jdbc:postgresql://... 以及 postgresql+psycopg://... 这类配置，
    # 统一转换为 psycopg 可直接使用的 PostgreSQL URL。
    normalized_url = safe_url[5:] if safe_url.startswith("jdbc:") else safe_url
    parsed = urlsplit(normalized_url)
    if not parsed.scheme:
        return normalized_url

    normalized_scheme = parsed.scheme.split("+", 1)[0]
    normalized_url = urlunsplit(
        (
            normalized_scheme,
            parsed.netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
    parsed = urlsplit(normalized_url)
    if parsed.username:
        return normalized_url

    safe_username = (username or "").strip()
    safe_password = (password or "").strip()
    if not safe_username:
        return normalized_url

    auth = quote(safe_username, safe="")
    if safe_password:
        auth += f":{quote(safe_password, safe='')}"

    return urlunsplit(
        (
            parsed.scheme,
            f"{auth}@{parsed.netloc}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


def build_vector_store(settings: Settings | None = None) -> VectorStorePort:
    resolved = settings or get_settings()
    # 向量库既支持直接把账号密码写进 URL，
    # 也支持 URL + 独立 PGVECTOR_DATASOURCE_USERNAME/PASSWORD 组合配置。
    return PgVectorStoreAdapter(
        connection_url=_resolve_pgvector_connection_url(
            datasource_url=resolved.pgvector_datasource_url,
            username=resolved.pgvector_datasource_username,
            password=resolved.pgvector_datasource_password,
        ),
        embedding_client=build_embedding_client(resolved),
        embedding_model_name=resolved.embedding_model_name,
        connect_timeout_seconds=resolved.pgvector_connect_timeout_seconds,
    )


def build_file_parser(settings: Settings | None = None) -> FileParserPort:
    # 当前文件解析器不依赖 settings，但保留统一签名，便于后续替换实现。
    _ = settings
    return FileParserAdapter()


def build_image_markdown_ocr_client(settings: Settings | None = None) -> ImageMarkdownOcrPort:
    resolved = settings or get_settings()
    return OpenAIImageMarkdownOcrAdapter(
        api_key=resolved.openai_vision_api_key,
        model_name=resolved.openai_vision_model,
        detail=resolved.openai_vision_detail,
        base_url=resolved.openai_vision_base_url,
        timeout_seconds=resolved.openai_vision_timeout_seconds,
    )


def build_embedding_client(settings: Settings | None = None) -> EmbeddingPort:
    resolved = settings or get_settings()
    # 这里是 embedding provider 的唯一选择入口：
    # application/domain 只依赖 EmbeddingPort，不感知 openai/ollama 差异。
    if resolved.embedding_provider == "ollama":
        return OllamaEmbeddingAdapter(
            model_name=resolved.ollama_embedding_model,
            base_url=resolved.ollama_embedding_base_url,
            timeout_seconds=resolved.ollama_embedding_timeout_seconds,
        )

    return OpenAIEmbeddingAdapter(
        api_key=resolved.openai_embedding_api_key,
        model_name=resolved.openai_embedding_model,
        base_url=resolved.openai_embedding_base_url,
        timeout_seconds=resolved.openai_embedding_timeout_seconds,
    )


def build_document_chunking_service(settings: Settings | None = None) -> DocumentChunkingService:
    resolved = settings or get_settings()
    return DocumentChunkingService(
        chunk_size=resolved.rag_chunk_size,
        chunk_overlap=resolved.rag_chunk_overlap,
    )


def build_logical_document_splitter_service() -> LogicalDocumentSplitterService:
    return LogicalDocumentSplitterService()


def build_rag_retriever(settings: Settings | None = None) -> RagRetrieverService:
    return RagRetrieverService(vector_store=build_vector_store(settings))


def build_agent_runtime(settings: Settings | None = None) -> AgentRuntimePort:
    resolved = settings or get_settings()
    return AutoGenAgentRuntimeAdapter(enabled=resolved.autogen_enabled)


def build_interview_session_repository(settings: Settings | None = None) -> InterviewSessionRepository:
    resolved = settings or get_settings()
    return MySqlInterviewSessionRepository(
        datasource_url=resolved.mysql_datasource_url,
        username=resolved.mysql_datasource_username,
        password=resolved.mysql_datasource_password,
    )


def build_auth_user_repository(settings: Settings | None = None) -> AuthUserRepository:
    resolved = settings or get_settings()
    return MySqlAuthUserRepository(
        datasource_url=resolved.mysql_datasource_url,
        username=resolved.mysql_datasource_username,
        password=resolved.mysql_datasource_password,
    )


def build_auth_service(settings: Settings | None = None) -> AuthService:
    resolved = settings or get_settings()
    security = AuthSecurityAdapter(
        token_secret=resolved.auth_token_secret,
        token_ttl_seconds=resolved.auth_token_ttl_seconds,
    )
    mail_sender = SmtpAuthMailAdapter(
        host=resolved.mail_host,
        port=resolved.mail_port,
        username=resolved.mail_username,
        authorization_code=resolved.mail_authorization_code,
        connection_timeout_seconds=resolved.mail_connection_timeout_seconds,
        io_timeout_seconds=max(resolved.mail_timeout_seconds, resolved.mail_write_timeout_seconds),
    )
    return AuthService(
        repository=build_auth_user_repository(resolved),
        security=security,
        mail_sender=mail_sender,
        email_code_secret=resolved.auth_email_code_secret,
        email_code_cooldown_seconds=resolved.auth_email_code_cooldown_seconds,
        email_code_expiry_seconds=resolved.auth_email_code_expiry_seconds,
        email_code_max_failed_attempts=resolved.auth_email_code_max_failed_attempts,
    )


def build_resume_repository(settings: Settings | None = None) -> ResumeRepository:
    resolved = settings or get_settings()
    return MySqlResumeRepository(
        datasource_url=resolved.mysql_datasource_url,
        username=resolved.mysql_datasource_username,
        password=resolved.mysql_datasource_password,
    )


def build_interview_graph(settings: Settings | None = None) -> InterviewGraph:
    resolved = settings or get_settings()
    _LOGGER.warning("[AI面试][构建] build_interview_graph start")
    chat_client = build_chat_client(resolved)
    _LOGGER.warning("[AI面试][构建] chat_client ready")
    rag_retriever = build_rag_retriever(resolved)
    _LOGGER.warning("[AI面试][构建] rag_retriever ready")
    agent_runtime = build_agent_runtime(resolved)
    _LOGGER.warning("[AI面试][构建] agent_runtime ready")

    return InterviewGraph(
        llm_client=chat_client,
        rag_retriever=rag_retriever,
        autogen_runtime=agent_runtime,
        rag_top_k=resolved.app_interview_rag_top_k,
        rag_similarity_threshold=resolved.app_interview_rag_similarity_threshold,
        rag_timeout_seconds=resolved.app_interview_rag_timeout_seconds,
    )
