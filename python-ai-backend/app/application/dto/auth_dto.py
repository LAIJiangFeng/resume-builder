# author: jf
from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.auth import AuthAccount


@dataclass(frozen=True, slots=True)
class AuthEncryptedLoginCommand:
    username: str
    key_id: str
    encrypted_key: str
    iv: str
    encrypted_password: str
    issued_at: int
    request_id: str


@dataclass(frozen=True, slots=True)
class AuthRegisterCommand:
    email: str
    verification_code: str
    password: str
    display_name: str


@dataclass(frozen=True, slots=True)
class AuthPasswordResetCommand:
    email: str
    verification_code: str
    new_password: str


@dataclass(frozen=True, slots=True)
class AuthLoginKey:
    algorithm: str
    key_id: str
    public_key: str


@dataclass(frozen=True, slots=True)
class AuthSession:
    access_token: str
    account: AuthAccount


@dataclass(frozen=True, slots=True)
class AuthEmailCodeWindow:
    cooldown_seconds: int
    expires_in_seconds: int


@dataclass(frozen=True, slots=True)
class AuthTokenClaims:
    user_id: str
    username: str
    password_version: str


@dataclass(frozen=True, slots=True)
class AuthUserContext:
    user_id: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
