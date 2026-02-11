"""
Chat router — POST /chat endpoint.

Receives user questions, runs the RAG pipeline, and returns
grounded answers with citations.
"""

from fastapi import APIRouter, Depends

from app.core.security import UserClaims, get_current_user
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


def get_rag_orchestrator():
    """
    Dependency injection for the RAG orchestrator.
    Initialized once in main.py and stored in app.state.
    """
    from app.main import app

    return app.state.rag_orchestrator


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: UserClaims = Depends(get_current_user),
    rag=Depends(get_rag_orchestrator),
) -> ChatResponse:
    """
    Ask the Security Policy Assistant a question.

    The endpoint:
    1. Validates user identity (via EasyAuth headers).
    2. Runs hybrid retrieval with security trimming.
    3. Generates a grounded answer with citations.
    4. Verifies citations before returning the response.
    """
    return await rag.answer(messages=request.messages, user=user)
