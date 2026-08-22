# author: jf
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AuthAccount:
    id: str
    username: str
    password_hash: str
    display_name: str
    role: str
    permissions: tuple[str, ...]


class AuthUserAlreadyExistsError(RuntimeError):
    pass


class AuthUserRepository(Protocol):
    def find_by_username(self, username: str) -> AuthAccount | None: ...

    def create_user(self, account: AuthAccount) -> AuthAccount: ...
