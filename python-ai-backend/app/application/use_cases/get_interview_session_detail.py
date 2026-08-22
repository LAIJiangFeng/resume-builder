# author: jf
from app.application.services.interview_session_service import (
    get_interview_session_detail as get_interview_session_detail_service,
)
from app.bootstrap.container import build_interview_session_repository, resolve_settings


def get_interview_session_detail(session_id: str, user_id: str) -> dict:
    settings = resolve_settings()
    repository = build_interview_session_repository(settings)
    return get_interview_session_detail_service(session_id, user_id, repository)
