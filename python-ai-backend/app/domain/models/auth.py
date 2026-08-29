# author: jf
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AuthEmailPurpose(str, Enum):
    REGISTRATION = "registration"
    PASSWORD_RESET = "password-reset"


@dataclass(frozen=True, slots=True)
class AuthAccount:
    id: str
    username: str
    password_hash: str
    display_name: str
    role: str
    permissions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AuthEmailVerification:
    email: str
    code_hash: str
    expires_at: datetime
    resend_available_at: datetime
    failed_attempts: int
