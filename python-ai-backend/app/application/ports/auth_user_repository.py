# author: jf
from __future__ import annotations

from typing import ContextManager, Protocol

from app.domain.models.auth import AuthAccount, AuthEmailVerification


class AuthRepositoryTransaction(Protocol):
    def find_by_username(
        self, username: str, *, enabled_only: bool
    ) -> AuthAccount | None: ...

    def create_user(self, account: AuthAccount) -> None: ...

    def update_password_hash(self, user_id: str, password_hash: str) -> bool: ...

    def find_verification_for_update(
        self, email: str
    ) -> AuthEmailVerification | None: ...

    def save_verification(self, verification: AuthEmailVerification) -> None: ...

    def increment_verification_failed_attempts(self, email: str) -> None: ...

    def delete_verification(self, email: str) -> None: ...


class AuthUserRepository(Protocol):
    def transaction(self) -> ContextManager[AuthRepositoryTransaction]: ...
