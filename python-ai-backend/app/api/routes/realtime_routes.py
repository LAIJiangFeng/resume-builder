# author: jf
from fastapi import APIRouter, Depends

from app.api.deps.auth import AuthUserContext, require_auth_user_context
from app.api.mappers.realtime_mapper import realtime_request_to_dto, realtime_response_from_dto
from app.api.schemas.realtime import RealtimeClientSecretRequest, RealtimeClientSecretResponse
from app.application.use_cases.create_realtime_client_secret import (
    create_realtime_client_secret as create_realtime_client_secret_use_case,
)

router = APIRouter(prefix="/api/ai", tags=["ai-realtime"])


@router.post("/realtime/client-secret", response_model=RealtimeClientSecretResponse)
def create_realtime_client_secret_route(
    request: RealtimeClientSecretRequest | None = None,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> RealtimeClientSecretResponse:
    _ = user_context
    return realtime_response_from_dto(
        create_realtime_client_secret_use_case(realtime_request_to_dto(request))
    )
