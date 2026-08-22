# author: jf
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.application.dto.interview_dto import InterviewTurnRequestDto
from app.application.ports.interview_session_repository import InterviewSessionRepository


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_role(raw_role: str) -> str:
    return "assistant" if str(raw_role).strip().lower() == "assistant" else "user"


def _normalize_score(raw_score: Any) -> dict[str, Any] | None:
    if not isinstance(raw_score, dict):
        return None
    raw_value = raw_score.get("score")
    try:
        parsed_score = int(raw_value if raw_value is not None else 0)
    except (TypeError, ValueError):
        parsed_score = 0
    return {
        "score": max(0, min(100, parsed_score)),
        "comment": str(raw_score.get("comment") or "").strip(),
    }


def _ensure_messages(session: dict[str, Any]) -> list[dict[str, Any]]:
    messages = session.get("messages")
    if isinstance(messages, list):
        return messages
    session["messages"] = []
    return session["messages"]


def _append_message_if_needed(
    messages: list[dict[str, Any]],
    *,
    role: str,
    content: str,
    score: dict[str, Any] | None,
) -> None:
    safe_content = str(content or "").strip()
    if not safe_content:
        return

    last_message = messages[-1] if messages else None
    if isinstance(last_message, dict):
        last_role = _normalize_role(str(last_message.get("role") or ""))
        last_content = str(last_message.get("content") or "").strip()
        if last_role == role and last_content == safe_content:
            return

    messages.append({"role": role, "content": safe_content, "score": score})


def _new_session_record(session_id: str, request: InterviewTurnRequestDto, now_iso: str) -> dict[str, Any]:
    initial_messages = [
        {
            "role": _normalize_role(item.role),
            "content": item.content.strip(),
            "score": item.score.model_dump() if item.score else None,
        }
        for item in request.history
        if item.content.strip()
    ]
    return {
        "sessionId": session_id,
        "userId": request.user_id,
        "mode": "interviewer" if request.mode == "interviewer" else "candidate",
        "status": "active",
        "durationMinutes": max(1, int(request.duration_minutes or 60)),
        "elapsedSeconds": max(0, int(request.elapsed_seconds or 0)),
        "memorySummary": str(request.memory_summary or "").strip(),
        "finalEvaluation": None,
        "resumeSnapshot": request.resume_snapshot or None,
        "messages": initial_messages,
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }


def persist_turn_result(
    request: InterviewTurnRequestDto,
    graph_output: dict[str, Any],
    repository: InterviewSessionRepository,
) -> dict[str, Any]:
    session_id = str(graph_output.get("sessionId") or request.session_id or "")
    assistant_reply = str(graph_output.get("assistantReply") or "").strip()
    memory_summary = str(graph_output.get("memorySummary") or request.memory_summary or "").strip()
    phase = str(graph_output.get("phase") or "opening")
    next_action = "finish" if str(graph_output.get("nextAction")) == "finish" else "continue"
    turn_score = _normalize_score(graph_output.get("turnScore"))
    final_evaluation = graph_output.get("finalEvaluation") if isinstance(graph_output.get("finalEvaluation"), dict) else None
    sources = list(graph_output.get("sources") or [])
    meta = graph_output.get("meta") if isinstance(graph_output.get("meta"), dict) else {}

    now_iso = _now_iso()
    session = repository.get(session_id, request.user_id)
    if session is None:
        session = _new_session_record(session_id=session_id, request=request, now_iso=now_iso)
    messages = _ensure_messages(session)

    user_input = str(request.user_input or "").strip()
    if user_input:
        _append_message_if_needed(messages, role="user", content=user_input, score=None)

    _append_message_if_needed(messages, role="assistant", content=assistant_reply, score=turn_score)
    session["memorySummary"] = memory_summary
    session["durationMinutes"] = max(1, int(request.duration_minutes or session.get("durationMinutes", 60)))
    session["elapsedSeconds"] = max(0, int(request.elapsed_seconds or session.get("elapsedSeconds", 0)))
    session["mode"] = "interviewer" if request.mode == "interviewer" else "candidate"
    session["status"] = "finished" if request.command == "finish" or next_action == "finish" else "active"
    session["resumeSnapshot"] = request.resume_snapshot or session.get("resumeSnapshot")
    if final_evaluation is not None:
        session["finalEvaluation"] = final_evaluation
    session["updatedAt"] = now_iso
    session["userId"] = request.user_id
    repository.save(session_id, request.user_id, session)

    return {
        "assistantReply": assistant_reply,
        "phase": phase,
        "nextAction": next_action,
        "turnScore": turn_score,
        "finalEvaluation": final_evaluation,
        "memorySummary": memory_summary,
        "sessionId": session_id,
        "sources": sources,
        "meta": meta,
    }


def _session_to_summary(session: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, Any]] = session.get("messages", [])
    final_evaluation = session.get("finalEvaluation")
    return {
        "sessionId": session.get("sessionId"),
        "userId": session.get("userId"),
        "mode": session.get("mode", "candidate"),
        "status": session.get("status", "active"),
        "durationMinutes": session.get("durationMinutes", 60),
        "elapsedSeconds": session.get("elapsedSeconds", 0),
        "messageCount": len(messages),
        "totalScore": final_evaluation.get("totalScore") if isinstance(final_evaluation, dict) else None,
        "passed": final_evaluation.get("passed") if isinstance(final_evaluation, dict) else None,
        "lastMessagePreview": str(messages[-1].get("content") if messages else "")[:120],
        "createdAt": session.get("createdAt", ""),
        "updatedAt": session.get("updatedAt", ""),
    }


def _session_to_detail(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "sessionId": session.get("sessionId"),
        "mode": session.get("mode", "candidate"),
        "status": session.get("status", "active"),
        "durationMinutes": session.get("durationMinutes", 60),
        "elapsedSeconds": session.get("elapsedSeconds", 0),
        "memorySummary": session.get("memorySummary", ""),
        "finalEvaluation": session.get("finalEvaluation"),
        "resumeSnapshot": session.get("resumeSnapshot"),
        "messages": session.get("messages", []),
        "createdAt": session.get("createdAt", ""),
        "updatedAt": session.get("updatedAt", ""),
    }


def list_interview_sessions(limit: int, user_id: str, repository: InterviewSessionRepository) -> list[dict[str, Any]]:
    safe_user_id = str(user_id or "").strip()
    if not safe_user_id:
        raise HTTPException(status_code=401, detail="请先登录后再查看面试历史")

    sessions = repository.list(limit, safe_user_id)
    sessions.sort(key=lambda item: str(item.get("updatedAt") or ""), reverse=True)
    return [_session_to_summary(item) for item in sessions[:limit]]


def get_interview_session_detail(session_id: str, user_id: str, repository: InterviewSessionRepository) -> dict[str, Any]:
    safe_user_id = str(user_id or "").strip()
    safe_session_id = session_id.strip()
    if not safe_user_id:
        raise HTTPException(status_code=401, detail="请先登录后再查看面试详情")
    if not safe_session_id:
        raise HTTPException(status_code=400, detail="sessionId cannot be empty")

    session = repository.get(safe_session_id, safe_user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return _session_to_detail(session)
