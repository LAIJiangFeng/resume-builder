# author: jf
"""Route registry for FastAPI."""

from app.api.routes.auth_routes import router as auth_router
from app.api.routes.chat_routes import router as chat_router
from app.api.routes.interview_routes import router as interview_router
from app.api.routes.rag_routes import router as rag_router
from app.api.routes.realtime_routes import router as realtime_router
from app.api.routes.resume_routes import router as resume_router

ALL_ROUTERS = (auth_router, chat_router, rag_router, interview_router, realtime_router, resume_router)

__all__ = [
    "ALL_ROUTERS",
    "auth_router",
    "chat_router",
    "rag_router",
    "interview_router",
    "realtime_router",
    "resume_router",
]
