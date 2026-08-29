# author: jf
from typing import Protocol

from app.domain.models.auth import AuthEmailPurpose


class AuthMailPort(Protocol):
    def ensure_configured(self) -> None: ...

    def send_verification_code(
        self,
        *,
        email: str,
        code: str,
        purpose: AuthEmailPurpose,
        valid_minutes: int,
    ) -> None: ...
