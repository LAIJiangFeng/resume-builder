# author: jf
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps.auth import AuthUserContext, require_auth_user_context
from app.api.mappers.interview_mapper import interview_turn_request_to_dto
from app.api.schemas.interview import InterviewTurnRequest
from app.application.use_cases.generate_interview_turn import (
    generate_interview_turn_stream as generate_interview_turn_stream_use_case,
)
from app.application.use_cases.get_interview_session_detail import (
    get_interview_session_detail as get_interview_session_detail_use_case,
)
from app.application.use_cases.list_interview_sessions import (
    list_interview_sessions as list_interview_sessions_use_case,
)

router = APIRouter(prefix="/api/ai/interview", tags=["ai-interview"])


@router.post("/turn/stream")
def interview_turn_stream(
    request: InterviewTurnRequest,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> StreamingResponse:
    return StreamingResponse(
        generate_interview_turn_stream_use_case(interview_turn_request_to_dto(request, user_context.user_id)),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
def list_interview_sessions_route(
    limit: int = Query(default=20, ge=1, le=200),
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> list[dict[str, Any]]:
    return list_interview_sessions_use_case(limit, user_context.user_id)


@router.get("/sessions/{session_id}")
def get_interview_session_detail_route(
    session_id: str,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> dict[str, Any]:
    return get_interview_session_detail_use_case(session_id, user_context.user_id)
