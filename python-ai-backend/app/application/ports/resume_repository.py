# author: jf
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class StoredResume:
    resume_id: str
    user_id: str
    name: str
    data: dict[str, Any]
    active: bool
    created_at: datetime
    updated_at: datetime


class ResumeNotFoundError(RuntimeError):
    pass


class LastResumeDeletionError(RuntimeError):
    pass


class ResumeRepository(Protocol):
    def list_by_user(self, user_id: str) -> list[StoredResume]: ...

    def get_owned(self, user_id: str, resume_id: str) -> StoredResume | None: ...

    def create(self, user_id: str, name: str, data: dict[str, Any]) -> StoredResume: ...

    def update(self, user_id: str, resume_id: str, name: str, data: dict[str, Any]) -> StoredResume: ...

    def activate(self, user_id: str, resume_id: str) -> StoredResume: ...

    def duplicate(self, user_id: str, resume_id: str, name: str) -> StoredResume: ...

    def delete(self, user_id: str, resume_id: str) -> None: ...
