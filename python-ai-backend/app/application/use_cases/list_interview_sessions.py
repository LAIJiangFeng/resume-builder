# author: jf
from app.application.services.interview_session_service import list_interview_sessions as list_interview_sessions_service
from app.bootstrap.container import build_interview_session_repository, resolve_settings


def list_interview_sessions(limit: int, user_id: str) -> list[dict]:
    settings = resolve_settings()
    repository = build_interview_session_repository(settings)
    return list_interview_sessions_service(limit, user_id, repository)
