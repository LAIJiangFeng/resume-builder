# author: jf
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps.auth import AuthUserContext, require_auth_user_context
from app.api.schemas.resume import ResumeCreateRequest, ResumeResponse, ResumeSummaryResponse, ResumeUpdateRequest
from app.application.ports.resume_repository import LastResumeDeletionError, ResumeNotFoundError, StoredResume
from app.application.services.resume_service import ResumeService
from app.bootstrap.container import build_resume_repository


router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@lru_cache(maxsize=1)
def _resume_service() -> ResumeService:
    return ResumeService(build_resume_repository())


@router.get("", response_model=list[ResumeSummaryResponse])
def list_resumes(user_context: AuthUserContext = Depends(require_auth_user_context)) -> list[ResumeSummaryResponse]:
    # 路由只做身份适配和响应映射，实际账号隔离与事务规则由用例和仓储层处理。
    return [_to_summary_response(item) for item in _resume_service().list_resumes(user_context.user_id)]


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def create_resume(
    request: ResumeCreateRequest | None = None,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> ResumeResponse:
    payload = request or ResumeCreateRequest()
    try:
        return _to_response(_resume_service().create_resume(user_context.user_id, payload.name, payload.data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: str,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> ResumeResponse:
    return _handle_resume(lambda: _resume_service().get_resume(user_context.user_id, resume_id))


@router.put("/{resume_id}", response_model=ResumeResponse)
def update_resume(
    resume_id: str,
    request: ResumeUpdateRequest,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> ResumeResponse:
    return _handle_resume(
        lambda: _resume_service().update_resume(user_context.user_id, resume_id, request.name, request.data)
    )


@router.post("/{resume_id}/activate", response_model=ResumeResponse)
def activate_resume(
    resume_id: str,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> ResumeResponse:
    return _handle_resume(lambda: _resume_service().activate_resume(user_context.user_id, resume_id))


@router.post("/{resume_id}/duplicate", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def duplicate_resume(
    resume_id: str,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> ResumeResponse:
    return _handle_resume(lambda: _resume_service().duplicate_resume(user_context.user_id, resume_id))


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: str,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> Response:
    try:
        _resume_service().delete_resume(user_context.user_id, resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="简历不存在") from exc
    except LastResumeDeletionError as exc:
        raise HTTPException(status_code=409, detail="至少需要保留一份简历") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _handle_resume(action) -> ResumeResponse:
    try:
        return _to_response(action())
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="简历不存在") from exc
    except LastResumeDeletionError as exc:
        raise HTTPException(status_code=409, detail="至少需要保留一份简历") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _to_summary_response(resume: StoredResume) -> ResumeSummaryResponse:
    return ResumeSummaryResponse(
        resumeId=resume.resume_id,
        name=resume.name,
        active=resume.active,
        createdAt=resume.created_at,
        updatedAt=resume.updated_at,
    )


def _to_response(resume: StoredResume) -> ResumeResponse:
    return ResumeResponse(data=resume.data, **_to_summary_response(resume).model_dump())
