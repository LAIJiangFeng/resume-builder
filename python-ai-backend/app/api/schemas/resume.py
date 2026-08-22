# author: jf
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ResumeCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    data: dict[str, Any] | None = None


class ResumeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    data: dict[str, Any]


class ResumeSummaryResponse(BaseModel):
    resumeId: str
    name: str
    active: bool
    createdAt: datetime
    updatedAt: datetime


class ResumeResponse(ResumeSummaryResponse):
    data: dict[str, Any]
