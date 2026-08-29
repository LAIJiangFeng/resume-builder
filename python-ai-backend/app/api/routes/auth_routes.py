# author: jf
from fastapi import APIRouter, Depends, Response

from app.api.deps.auth import get_auth_service
from app.api.schemas.auth import (
    AuthEmailCodeRequest,
    AuthEmailCodeResponse,
    AuthLoginKeyResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthPasswordResetRequest,
    AuthRegisterRequest,
    AuthUserResponse,
)
from app.application.dto.auth_dto import (
    AuthEncryptedLoginCommand,
    AuthPasswordResetCommand,
    AuthRegisterCommand,
    AuthSession,
)
from app.application.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login-key", response_model=AuthLoginKeyResponse)
def get_login_key(
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthLoginKeyResponse:
    # 公钥属于当前进程，禁止浏览器或代理缓存服务重启前的旧密钥。
    response.headers["Cache-Control"] = "no-store"
    login_key = auth_service.get_login_key()
    return AuthLoginKeyResponse(
        algorithm=login_key.algorithm,
        keyId=login_key.key_id,
        publicKey=login_key.public_key,
    )


@router.post("/login", response_model=AuthLoginResponse)
def login(
    request: AuthLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthLoginResponse:
    session = auth_service.login(
        AuthEncryptedLoginCommand(
            username=request.username,
            key_id=request.keyId,
            encrypted_key=request.encryptedKey,
            iv=request.iv,
            encrypted_password=request.encryptedPassword,
            issued_at=request.issuedAt,
            request_id=request.requestId,
        )
    )
    return _to_login_response(session)


@router.post("/email-code", response_model=AuthEmailCodeResponse)
def send_registration_email_code(
    request: AuthEmailCodeRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthEmailCodeResponse:
    window = auth_service.send_registration_email_code(request.email)
    return AuthEmailCodeResponse(
        cooldownSeconds=window.cooldown_seconds,
        expiresInSeconds=window.expires_in_seconds,
    )


@router.post("/password-reset/email-code", response_model=AuthEmailCodeResponse)
def send_password_reset_email_code(
    request: AuthEmailCodeRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthEmailCodeResponse:
    window = auth_service.send_password_reset_email_code(request.email)
    return AuthEmailCodeResponse(
        cooldownSeconds=window.cooldown_seconds,
        expiresInSeconds=window.expires_in_seconds,
    )


@router.post("/register", response_model=AuthLoginResponse)
def register(
    request: AuthRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthLoginResponse:
    session = auth_service.register(
        AuthRegisterCommand(
            email=request.email,
            verification_code=request.verificationCode,
            password=request.password,
            display_name=request.displayName,
        )
    )
    return _to_login_response(session)


@router.post("/password-reset", response_class=Response)
def reset_password(
    request: AuthPasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    auth_service.reset_password(
        AuthPasswordResetCommand(
            email=request.email,
            verification_code=request.verificationCode,
            new_password=request.newPassword,
        )
    )
    return Response(status_code=200)


def _to_login_response(session: AuthSession) -> AuthLoginResponse:
    account = session.account
    return AuthLoginResponse(
        accessToken=session.access_token,
        user=AuthUserResponse(
            id=account.id,
            username=account.username,
            displayName=account.display_name,
            role=account.role,
            permissions=list(account.permissions),
        ),
    )
