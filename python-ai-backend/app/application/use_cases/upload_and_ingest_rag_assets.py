# author: jf
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.application.dto.rag_dto import RagUploadAssetDto, RagUploadFileResultDto, RagUploadResponseDto
from app.bootstrap.container import (
    build_document_chunking_service,
    build_embedding_client,
    build_file_parser,
    build_image_markdown_ocr_client,
    build_logical_document_splitter_service,
    build_vector_store,
    resolve_settings,
)
from app.domain.exceptions.rag_exceptions import (
    FileParseError,
    FileTooLargeError,
    RagIngestError,
    UnsupportedFileTypeError,
)
from app.domain.models.rag_document import ExtractedDocument, RagChunk
from app.infrastructure.text.markdown_structure_normalizer import MarkdownStructureNormalizer

_SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".png", ".jpg", ".jpeg", ".webp"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_UPLOAD_READ_CHUNK_SIZE = 1024 * 1024
_UPLOAD_STAGE_PROGRESS = {
    "排队": 0.0,
    "开始": 0.08,
    "读取": 0.16,
    "校验": 0.25,
    "解析": 0.38,
    "规范化": 0.50,
    "逻辑文档拆分": 0.60,
    "切块": 0.72,
    "Embedding": 0.84,
    "入库": 0.94,
    "完成": 1.0,
}
RagUploadProgressCallback = Callable[[dict[str, Any]], None]


def upload_and_ingest_rag_assets(
    assets: list[RagUploadAssetDto],
    trace_id: str | None = None,
    progress_callback: RagUploadProgressCallback | None = None,
) -> RagUploadResponseDto:
    safe_trace_id = _normalize_trace_id(trace_id)
    _log_upload(safe_trace_id, "请求", "开始处理上传请求", file_count=len(assets))
    _emit_progress(
        progress_callback,
        "batch-start",
        trace_id=safe_trace_id,
        total_files=len(assets),
        status="uploading",
        stage="开始",
        progress_percent=0,
        message="开始处理批量上传",
    )

    settings = resolve_settings()
    _emit_progress(
        progress_callback,
        "batch-stage",
        trace_id=safe_trace_id,
        stage="校验",
        status="uploading",
        progress_percent=1 if assets else 0,
        message="开始批量基础校验",
    )
    _log_upload(
        safe_trace_id,
        "校验",
        "开始批量基础校验",
        max_file_size_mb=settings.rag_max_file_size_mb,
    )
    _validate_assets(assets=assets)
    _log_upload(safe_trace_id, "校验", "批量基础校验通过")
    _emit_progress(
        progress_callback,
        "batch-stage",
        trace_id=safe_trace_id,
        stage="初始化",
        status="uploading",
        progress_percent=2 if assets else 0,
        message="校验通过，正在初始化处理依赖",
    )

    # 业务意图：
    # 1) application 层统一编排文件解析、图片 OCR、切块、向量化和 pgvector 入库。
    # 2) 逐文件执行校验与处理，保证单个坏文件不会把整批上传直接打成 4xx/5xx。
    # 3) 响应必须按输入顺序返回每个文件的结果，方便前端逐项展示失败原因。
    file_parser = build_file_parser(settings)
    image_ocr = build_image_markdown_ocr_client(settings)
    embedding_client = build_embedding_client(settings)
    vector_store = build_vector_store(settings)
    chunking_service = build_document_chunking_service(settings)
    logical_document_splitter = build_logical_document_splitter_service()
    normalizer = MarkdownStructureNormalizer()
    _log_upload(safe_trace_id, "初始化", "依赖构建完成，进入逐文件处理")
    _emit_progress(
        progress_callback,
        "batch-stage",
        trace_id=safe_trace_id,
        stage="处理",
        status="uploading",
        progress_percent=3 if assets else 0,
        message="依赖初始化完成，进入逐文件处理",
    )

    results: list[RagUploadFileResultDto] = []
    inserted = 0

    for index, asset in enumerate(assets, start=1):
        source_type = _detect_source_type(asset.file_name)
        fallback_ingest_source = _default_ingest_source(source_type)
        _log_upload(
            safe_trace_id,
            "文件",
            "开始处理文件",
            index=index,
            file_name=asset.file_name,
            source_type=source_type,
        )
        _emit_progress(
            progress_callback,
            "file-start",
            trace_id=safe_trace_id,
            file_index=index,
            total_files=len(assets),
            file_name=asset.file_name,
            source_type=source_type,
            ingest_source=fallback_ingest_source,
            stage="读取",
            status="uploading",
            file_progress_percent=_file_stage_progress_percent("读取"),
            progress_percent=_overall_file_progress_percent(index, len(assets), "读取"),
            message="开始处理文件",
        )

        stage = "读取"
        try:
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在读取文件内容",
            )
            materialized_asset = _materialize_asset(
                asset=asset,
                max_file_size_mb=settings.rag_max_file_size_mb,
            )
            file_size_bytes = len(_require_file_bytes(materialized_asset))
            _log_upload(
                safe_trace_id,
                "读取",
                "文件流读取完成",
                file_name=asset.file_name,
                size_bytes=file_size_bytes,
            )

            stage = "校验"
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在校验文件格式和大小",
            )
            _validate_asset(asset=materialized_asset, max_file_size_mb=settings.rag_max_file_size_mb)
            _log_upload(safe_trace_id, "校验", "单文件校验通过", file_name=asset.file_name)

            stage = "解析"
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在解析文件内容",
            )
            extracted = _extract_document(
                asset=materialized_asset,
                file_parser=file_parser,
                image_ocr=image_ocr,
            )
            _log_upload(
                safe_trace_id,
                "解析",
                "文件内容解析完成",
                file_name=asset.file_name,
                ingest_source=extracted.ingest_source,
                content_chars=len(extracted.content),
            )

            stage = "规范化"
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在规范化文本结构",
            )
            normalized_content = normalizer.normalize(extracted.content)
            if not normalized_content:
                raise FileParseError(f"文件 {asset.file_name} 未生成可入库内容")
            extracted = ExtractedDocument(
                source_id=extracted.source_id,
                original_filename=extracted.original_filename,
                original_content_type=extracted.original_content_type,
                source_type=extracted.source_type,
                ingest_source=extracted.ingest_source,
                content=normalized_content,
                metadata=extracted.metadata,
            )
            _log_upload(
                safe_trace_id,
                "规范化",
                "文本规范化完成",
                file_name=asset.file_name,
                normalized_chars=len(normalized_content),
            )

            stage = "逻辑文档拆分"
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在拆分逻辑文档",
            )
            logical_documents = logical_document_splitter.split_document(extracted)
            if not logical_documents:
                raise FileParseError(f"文件 {asset.file_name} 未拆分出有效 logical document")
            _log_upload(
                safe_trace_id,
                "逻辑文档拆分",
                "逻辑文档拆分完成",
                file_name=asset.file_name,
                logical_document_count=len(logical_documents),
            )

            stage = "切块"
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在切分知识库 chunk",
            )
            chunks: list[RagChunk] = []
            for logical_document in logical_documents:
                chunks.extend(chunking_service.chunk_document(logical_document))
            if not chunks:
                raise FileParseError(f"文件 {asset.file_name} 未切分出有效 chunk")
            _assign_global_chunk_indexes(chunks)
            chunk_texts = [chunk.content for chunk in chunks]
            total_chars = sum(len(text) for text in chunk_texts)
            _log_upload(
                safe_trace_id,
                "切块",
                "文档切块完成",
                file_name=asset.file_name,
                logical_document_count=len(logical_documents),
                chunk_count=len(chunks),
                total_chunk_chars=total_chars,
            )

            stage = "Embedding"
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在生成 Embedding",
            )
            embedding_started_at = perf_counter()
            _emit_embedding_timing_log(
                trace_id=safe_trace_id,
                event="start",
                file_name=asset.file_name,
                source_type=extracted.source_type,
                ingest_source=extracted.ingest_source,
                chunk_count=len(chunk_texts),
                total_chars=total_chars,
                file_size_bytes=file_size_bytes,
                embedding_model=getattr(embedding_client, "model_name", None),
                embedding_base_url=getattr(embedding_client, "base_url", None),
            )
            try:
                embeddings = embedding_client.embed_texts(chunk_texts)
            except Exception as exc:
                _emit_embedding_timing_log(
                    trace_id=safe_trace_id,
                    event="failed",
                    file_name=asset.file_name,
                    source_type=extracted.source_type,
                    ingest_source=extracted.ingest_source,
                    chunk_count=len(chunk_texts),
                    total_chars=total_chars,
                    file_size_bytes=file_size_bytes,
                    elapsed_ms=(perf_counter() - embedding_started_at) * 1000,
                    embedding_model=getattr(embedding_client, "model_name", None),
                    embedding_base_url=getattr(embedding_client, "base_url", None),
                    error_message=str(exc),
                )
                raise
            _emit_embedding_timing_log(
                trace_id=safe_trace_id,
                event="finish",
                file_name=asset.file_name,
                source_type=extracted.source_type,
                ingest_source=extracted.ingest_source,
                chunk_count=len(chunk_texts),
                total_chars=total_chars,
                file_size_bytes=file_size_bytes,
                elapsed_ms=(perf_counter() - embedding_started_at) * 1000,
                embedding_model=getattr(embedding_client, "model_name", None),
                embedding_base_url=getattr(embedding_client, "base_url", None),
                vector_count=len(embeddings),
            )

            stage = "入库"
            _emit_file_stage(
                progress_callback,
                safe_trace_id,
                index,
                len(assets),
                asset.file_name,
                stage,
                "正在写入 pgvector",
            )
            _log_upload(
                safe_trace_id,
                "入库",
                "开始写入向量库",
                file_name=asset.file_name,
                vector_count=len(embeddings),
            )
            inserted_count = vector_store.add_documents_with_embeddings(
                documents=[
                    {
                        "source_id": chunk.source_id,
                        "content": chunk.content,
                        "metadata": chunk.metadata,
                    }
                    for chunk in chunks
                ],
                embeddings=embeddings,
            )
            inserted += inserted_count
            _log_upload(
                safe_trace_id,
                "入库",
                "向量库写入完成",
                file_name=asset.file_name,
                inserted_count=inserted_count,
            )

            result = RagUploadFileResultDto(
                file_name=asset.file_name,
                content_type=materialized_asset.content_type,
                source_type=extracted.source_type,
                ingest_source=extracted.ingest_source,
                chunk_count=len(chunks),
                inserted_count=inserted_count,
                status="success",
            )
            results.append(result)
            _emit_file_result(progress_callback, safe_trace_id, index, len(assets), result)
            _log_upload(safe_trace_id, "文件", "文件处理成功", file_name=asset.file_name)
        except RagIngestError as exc:
            # 异常与兜底策略：
            # 1) 只吞掉明确的 RAG 业务异常，保持逐文件失败契约。
            # 2) 未知异常继续上抛，让调用链按 500 暴露真实问题，避免静默掩盖程序错误。
            _log_upload(
                safe_trace_id,
                "异常",
                "文件处理失败",
                file_name=asset.file_name,
                stage=stage,
                error=str(exc),
            )
            result = RagUploadFileResultDto(
                file_name=asset.file_name,
                content_type=asset.content_type,
                source_type=source_type,
                ingest_source=fallback_ingest_source,
                chunk_count=0,
                inserted_count=0,
                status="failed",
                error_message=str(exc),
            )
            results.append(result)
            _emit_file_result(progress_callback, safe_trace_id, index, len(assets), result, stage=stage)

    response = RagUploadResponseDto(
        total_files=len(assets),
        succeeded_files=sum(1 for item in results if item.status == "success"),
        failed_files=sum(1 for item in results if item.status == "failed"),
        inserted=inserted,
        files=results,
    )
    _log_upload(
        safe_trace_id,
        "完成",
        "上传请求处理结束",
        total_files=response.total_files,
        succeeded_files=response.succeeded_files,
        failed_files=response.failed_files,
        inserted=response.inserted,
    )
    _emit_progress(
        progress_callback,
        "batch-complete",
        trace_id=safe_trace_id,
        total_files=response.total_files,
        succeeded_files=response.succeeded_files,
        failed_files=response.failed_files,
        inserted=response.inserted,
        stage="完成",
        status="success" if response.failed_files == 0 else "failed",
        progress_percent=100,
        files=[_upload_result_to_progress_payload(item) for item in response.files],
        message="上传请求处理结束",
    )
    return response


def _validate_assets(assets: list[RagUploadAssetDto]) -> None:
    if not assets:
        raise FileParseError("至少需要上传一个文件")


def _validate_asset(asset: RagUploadAssetDto, max_file_size_mb: int) -> None:
    byte_limit = max(1, max_file_size_mb) * 1024 * 1024
    extension = Path(asset.file_name).suffix.lower()
    file_bytes = _require_file_bytes(asset)
    if extension not in _SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"暂不支持的文件类型: {extension or asset.content_type}")
    if not file_bytes:
        raise FileParseError(f"文件 {asset.file_name} 不能为空")
    if len(file_bytes) > byte_limit:
        raise FileTooLargeError(f"文件 {asset.file_name} 超过大小限制 {max_file_size_mb}MB")


def _extract_document(asset: RagUploadAssetDto, file_parser, image_ocr) -> ExtractedDocument:
    file_bytes = _require_file_bytes(asset)
    if _detect_source_type(asset.file_name) == "image":
        markdown = image_ocr.extract_markdown(
            image_bytes=file_bytes,
            file_name=asset.file_name,
            content_type=asset.content_type,
        )
        return ExtractedDocument(
            source_id=Path(asset.file_name).stem.strip() or asset.file_name,
            original_filename=asset.file_name,
            original_content_type=asset.content_type,
            source_type="image",
            ingest_source="image_ocr_text",
            content=markdown,
        )
    return file_parser.parse(
        file_bytes=file_bytes,
        file_name=asset.file_name,
        content_type=asset.content_type,
    )


def _materialize_asset(asset: RagUploadAssetDto, max_file_size_mb: int) -> RagUploadAssetDto:
    if asset.file_bytes is not None:
        return asset
    return RagUploadAssetDto(
        file_name=asset.file_name,
        content_type=asset.content_type,
        file_bytes=_read_file_bytes_with_limit(asset=asset, max_file_size_mb=max_file_size_mb),
    )


def _read_file_bytes_with_limit(asset: RagUploadAssetDto, max_file_size_mb: int) -> bytes:
    if asset.file_stream is None:
        raise FileParseError(f"文件 {asset.file_name} 缺少可读取内容")

    byte_limit = max(1, max_file_size_mb) * 1024 * 1024
    if hasattr(asset.file_stream, "seek"):
        asset.file_stream.seek(0)

    buffer = bytearray()
    while True:
        next_chunk_limit = min(_UPLOAD_READ_CHUNK_SIZE, (byte_limit - len(buffer)) + 1)
        chunk = asset.file_stream.read(next_chunk_limit)
        if not chunk:
            break
        if len(buffer) + len(chunk) > byte_limit:
            raise FileTooLargeError(f"文件 {asset.file_name} 超过大小限制 {max_file_size_mb}MB")
        buffer.extend(chunk)
    return bytes(buffer)


def _require_file_bytes(asset: RagUploadAssetDto) -> bytes:
    if asset.file_bytes is None:
        raise FileParseError(f"文件 {asset.file_name} 缺少可解析字节内容")
    return asset.file_bytes


def _detect_source_type(file_name: str) -> str:
    extension = Path(file_name).suffix.lower()
    return "image" if extension in _IMAGE_EXTENSIONS else "document"


def _default_ingest_source(source_type: str) -> str:
    return "image_ocr_text" if source_type == "image" else "text_document"


def _emit_file_stage(
    progress_callback: RagUploadProgressCallback | None,
    trace_id: str,
    file_index: int,
    total_files: int,
    file_name: str,
    stage: str,
    message: str,
) -> None:
    _emit_progress(
        progress_callback,
        "file-stage",
        trace_id=trace_id,
        file_index=file_index,
        total_files=total_files,
        file_name=file_name,
        stage=stage,
        status="uploading",
        file_progress_percent=_file_stage_progress_percent(stage),
        progress_percent=_overall_file_progress_percent(file_index, total_files, stage),
        message=message,
    )


def _emit_file_result(
    progress_callback: RagUploadProgressCallback | None,
    trace_id: str,
    file_index: int,
    total_files: int,
    result: RagUploadFileResultDto,
    stage: str = "完成",
) -> None:
    _emit_progress(
        progress_callback,
        "file-result",
        trace_id=trace_id,
        file_index=file_index,
        total_files=total_files,
        file_name=result.file_name,
        stage=stage,
        status=result.status,
        file_progress_percent=100,
        progress_percent=_overall_file_result_progress_percent(file_index, total_files),
        result=_upload_result_to_progress_payload(result),
        message="文件处理成功" if result.status == "success" else (result.error_message or "文件处理失败"),
    )


def _upload_result_to_progress_payload(result: RagUploadFileResultDto) -> dict[str, object]:
    return {
        "file_name": result.file_name,
        "content_type": result.content_type,
        "source_type": result.source_type,
        "ingest_source": result.ingest_source,
        "chunk_count": result.chunk_count,
        "inserted_count": result.inserted_count,
        "status": result.status,
        "error_message": result.error_message,
    }


def _emit_progress(
    progress_callback: RagUploadProgressCallback | None,
    event: str,
    **payload: object,
) -> None:
    if progress_callback is None:
        return
    progress_callback({"event": event, **payload})


def _file_stage_progress_percent(stage: str) -> int:
    stage_progress = _UPLOAD_STAGE_PROGRESS.get(stage)
    if stage_progress is None:
        stage_progress = 0.35
    return _clamp_percent(round(stage_progress * 100))


def _overall_file_progress_percent(file_index: int, total_files: int, stage: str) -> int:
    if total_files <= 0:
        return 0
    stage_progress = _UPLOAD_STAGE_PROGRESS.get(stage, 0.35)
    progress = round(((max(file_index, 1) - 1) + stage_progress) / total_files * 100)
    return min(99, max(1, _clamp_percent(progress)))


def _overall_file_result_progress_percent(file_index: int, total_files: int) -> int:
    if total_files <= 0:
        return 100
    progress = round(max(file_index, 1) / total_files * 100)
    return _clamp_percent(progress)


def _clamp_percent(value: int) -> int:
    return min(100, max(0, value))


def _emit_embedding_timing_log(
    *,
    trace_id: str,
    event: str,
    file_name: str,
    source_type: str,
    ingest_source: str,
    chunk_count: int,
    total_chars: int,
    file_size_bytes: int,
    elapsed_ms: float | None = None,
    vector_count: int | None = None,
    embedding_model: str | None = None,
    embedding_base_url: str | None = None,
    error_message: str | None = None,
) -> None:
    extra: dict[str, object] = {
        "event": event,
        "file_name": file_name,
        "source_type": source_type,
        "ingest_source": ingest_source,
        "chunk_count": chunk_count,
        "total_chars": total_chars,
        "file_size_bytes": file_size_bytes,
    }
    if elapsed_ms is not None:
        extra["elapsed_ms"] = f"{elapsed_ms:.2f}"
    if vector_count is not None:
        extra["vector_count"] = vector_count
    if embedding_model:
        extra["embedding_model"] = embedding_model
    if embedding_base_url:
        extra["embedding_base_url"] = embedding_base_url
    if error_message:
        extra["error"] = error_message
    _log_upload(trace_id, "Embedding", "Embedding 阶段日志", **extra)


def _normalize_trace_id(raw_trace_id: str | None) -> str:
    safe = (raw_trace_id or "").strip()
    if safe:
        return safe
    return uuid4().hex[:8]


def _log_upload(trace_id: str, log_stage: str, message: str, **extra: object) -> None:
    parts = [f"[知识库上传][trace={trace_id}][{log_stage}] {message}"]
    for key, value in extra.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), flush=True)


def _assign_global_chunk_indexes(chunks: list[RagChunk]) -> None:
    for index, chunk in enumerate(chunks):
        metadata = getattr(chunk, "metadata", None)
        if isinstance(metadata, dict):
            metadata["chunkIndex"] = index
