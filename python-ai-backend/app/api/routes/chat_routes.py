# author: jf
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps.auth import AuthUserContext, require_auth_user_context
from app.api.mappers.chat_mapper import chat_request_to_dto, chat_response_from_dto
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.application.use_cases.run_chat import run_chat as run_chat_use_case
from app.application.use_cases.stream_chat import generate_chat_stream as generate_chat_stream_use_case

router = APIRouter(prefix="/api/ai", tags=["ai-chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> ChatResponse:
    _ = user_context
    return chat_response_from_dto(run_chat_use_case(chat_request_to_dto(request)))


@router.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> StreamingResponse:
    _ = user_context
    return StreamingResponse(
        generate_chat_stream_use_case(chat_request_to_dto(request)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
