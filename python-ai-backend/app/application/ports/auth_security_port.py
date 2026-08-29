# author: jf
from typing import Protocol

from app.application.dto.auth_dto import (
    AuthEncryptedLoginCommand,
    AuthLoginKey,
    AuthTokenClaims,
)
from app.domain.models.auth import AuthAccount


class AuthSecurityPort(Protocol):
    def get_login_key(self) -> AuthLoginKey: ...

    def decrypt_login_password(self, command: AuthEncryptedLoginCommand) -> str: ...

    def hash_password(self, raw_password: str) -> str: ...

    def verify_password(self, raw_password: str, stored_password_hash: str) -> bool: ...

    def create_access_token(self, account: AuthAccount) -> str: ...

    def decode_access_token(self, token: str) -> AuthTokenClaims: ...

    def create_password_version(self, password_hash: str) -> str: ...
