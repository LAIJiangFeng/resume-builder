# author: jf
from app.api.schemas.interview import InterviewHistoryItem, InterviewTurnRequest
from app.application.dto.interview_dto import InterviewHistoryItemDto, InterviewTurnRequestDto, InterviewTurnScoreDto


def _history_item_to_dto(item: InterviewHistoryItem) -> InterviewHistoryItemDto:
    return InterviewHistoryItemDto(
        role=item.role,
        content=item.content,
        score=InterviewTurnScoreDto(score=item.score.score, comment=item.score.comment) if item.score else None,
    )


def interview_turn_request_to_dto(request: InterviewTurnRequest, user_id: str) -> InterviewTurnRequestDto:
    return InterviewTurnRequestDto(
        user_id=user_id,
        mode=request.mode,
        command=request.command,
        user_input=request.userInput,
        session_id=request.sessionId,
        memory_summary=request.memorySummary,
        duration_minutes=request.durationMinutes,
        elapsed_seconds=request.elapsedSeconds,
        history=[_history_item_to_dto(item) for item in request.history],
        resume_snapshot=request.resumeSnapshot,
    )
