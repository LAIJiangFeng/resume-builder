# author: jf
from fastapi import APIRouter, Response

from app.api.deps.auth import (
    authenticate_account,
    create_access_token,
    decrypt_login_password,
    get_login_encryption_key,
    register_account,
)
from app.api.schemas.auth import (
    AuthLoginKeyResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthRegisterRequest,
    AuthUserResponse,
)
from app.application.ports.auth_user_repository import AuthAccount

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login-key", response_model=AuthLoginKeyResponse)
def get_login_key(response: Response) -> AuthLoginKeyResponse:
    # 公钥按当前后端进程生成，禁止浏览器或代理缓存，避免服务重启后继续使用旧密钥。
    response.headers["Cache-Control"] = "no-store"
    algorithm, key_id, public_key = get_login_encryption_key()
    return AuthLoginKeyResponse(algorithm=algorithm, keyId=key_id, publicKey=public_key)


@router.post("/login", response_model=AuthLoginResponse)
def login(request: AuthLoginRequest) -> AuthLoginResponse:
    # HTTP 层只接收密文契约；解密、防重放和时效校验集中由认证依赖完成。
    password = decrypt_login_password(
        username=request.username,
        key_id=request.keyId,
        encrypted_key=request.encryptedKey,
        iv=request.iv,
        encrypted_password=request.encryptedPassword,
        issued_at=request.issuedAt,
        request_id=request.requestId,
    )
    account = authenticate_account(request.username, password)
    return _to_login_response(account)


@router.post("/register", response_model=AuthLoginResponse)
def register(request: AuthRegisterRequest) -> AuthLoginResponse:
    account = register_account(request.username, request.password, request.displayName)
    return _to_login_response(account)


def _to_login_response(account: AuthAccount) -> AuthLoginResponse:
    return AuthLoginResponse(
        accessToken=create_access_token(account),
        user=AuthUserResponse(
            id=account.id,
            username=account.username,
            displayName=account.display_name,
            role=account.role,
            permissions=list(account.permissions),
        ),
    )
