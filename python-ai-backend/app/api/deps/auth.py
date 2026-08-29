# author: jf
from functools import lru_cache

from fastapi import Depends, Header

from app.application.dto.auth_dto import AuthUserContext
from app.application.services.auth_service import AuthService
from app.bootstrap.container import build_auth_service


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    # 认证服务必须进程内复用，确保登录公钥和 requestId 防重放缓存保持稳定。
    return build_auth_service()


def require_auth_user_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUserContext:
    return auth_service.require_user(authorization)


def require_admin_user_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUserContext:
    return auth_service.require_admin(authorization)


__all__ = [
    "AuthUserContext",
    "get_auth_service",
    "require_admin_user_context",
    "require_auth_user_context",
]
