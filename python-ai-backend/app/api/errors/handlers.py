# author: jf
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions.auth_exceptions import (
    AuthConflictError,
    AuthError,
    AuthForbiddenError,
    AuthRateLimitError,
    AuthServiceUnavailableError,
    AuthStorageError,
    AuthUnauthorizedError,
    AuthValidationError,
)
from app.domain.exceptions.rag_exceptions import (
    EmbeddingError,
    FileParseError,
    FileTooLargeError,
    ImageOcrError,
    UnsupportedFileTypeError,
    VectorStoreError,
)


def register_error_handlers(app: FastAPI) -> None:
    # 这些 handler 只处理“请求级失败”。
    # 如果是批量上传里的单文件失败，use case 会把错误写到 files[]，不会走这里。
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # 对外只返回中文业务提示，不把 Pydantic 的英文类型、字段位置或原始输入暴露给页面。
        message = _resolve_validation_message(exc.errors())
        # 认证接口与 Spring 参数校验保持 400；其余既有 FastAPI 接口继续保留 422。
        status_code = 400 if request.url.path.startswith("/api/auth/") else 422
        return JSONResponse(status_code=status_code, content={"detail": message})

    @app.exception_handler(AuthError)
    async def handle_auth_error(_: Request, exc: AuthError) -> JSONResponse:
        if isinstance(exc, AuthValidationError):
            status_code = 400
        elif isinstance(exc, AuthUnauthorizedError):
            status_code = 401
        elif isinstance(exc, AuthForbiddenError):
            status_code = 403
        elif isinstance(exc, AuthConflictError):
            status_code = 409
        elif isinstance(exc, AuthRateLimitError):
            status_code = 429
        elif isinstance(exc, AuthServiceUnavailableError):
            status_code = 503
        elif isinstance(exc, AuthStorageError):
            status_code = 500
        else:
            status_code = 500
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    @app.exception_handler(UnsupportedFileTypeError)
    async def handle_unsupported_file_type(_: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(FileParseError)
    async def handle_file_parse_error(_: Request, exc: FileParseError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(FileTooLargeError)
    async def handle_file_too_large(_: Request, exc: FileTooLargeError) -> JSONResponse:
        return JSONResponse(status_code=413, content={"detail": str(exc)})

    @app.exception_handler(ImageOcrError)
    async def handle_image_ocr_error(_: Request, exc: ImageOcrError) -> JSONResponse:
        # OCR/Embedding 这类上游依赖错误，按 502 暴露更贴近网关/上游失败语义。
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(EmbeddingError)
    async def handle_embedding_error(_: Request, exc: EmbeddingError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(VectorStoreError)
    async def handle_vector_store_error(_: Request, exc: VectorStoreError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})


def _resolve_validation_message(errors: list[dict[str, object]]) -> str:
    if not errors:
        return "请求参数不合法"

    first_error = errors[0]
    location = first_error.get("loc")
    field_name = str(location[-1]) if isinstance(location, (list, tuple)) and location else ""
    field_labels = {
        "username": "登录账号",
        "password": "密码",
        "displayName": "姓名",
        "email": "邮箱",
        "verificationCode": "邮箱验证码",
        "newPassword": "新密码",
        "keyId": "登录密钥标识",
        "encryptedKey": "登录加密密钥",
        "iv": "登录加密随机数",
        "encryptedPassword": "登录密码密文",
        "issuedAt": "登录请求时间",
        "requestId": "登录请求标识",
    }
    field_label = field_labels.get(field_name, "请求参数")
    error_type = str(first_error.get("type") or "")

    if error_type == "missing":
        return f"{field_label}不能为空"
    if error_type == "extra_forbidden":
        return "请求包含不支持的参数"
    if error_type == "string_pattern_mismatch" and field_name == "verificationCode":
        return "邮箱验证码必须是 6 位数字"
    if error_type.startswith("string_too_short"):
        if field_name == "password":
            return "密码至少需要 8 个字符"
        if field_name == "newPassword":
            return "新密码长度必须在 8 到 128 位之间"
        return f"{field_label}长度不足"
    if error_type.startswith("string_too_long"):
        if field_name == "newPassword":
            return "新密码长度必须在 8 到 128 位之间"
        return f"{field_label}长度超出限制"
    if error_type.startswith("greater_than"):
        return f"{field_label}无效"
    return f"{field_label}格式不正确"
