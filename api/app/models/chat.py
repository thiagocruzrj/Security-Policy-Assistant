"""
Pydantic models for the Chat API request/response contracts.
"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request body for the POST /chat endpoint."""

    messages: list[ChatMessage] = Field(
        ..., description="Conversation history (latest message last)"
    )


class Source(BaseModel):
    """A source document referenced by a citation."""

    chunk_id: str = Field(..., description="Unique chunk identifier in the index")
    title: str = Field(..., description="Source document title")
    source_uri: str = Field("", description="URI to the original document in storage")


class Citation(BaseModel):
    """A citation linking an answer claim to a source chunk."""

    tag: str = Field(..., description="Citation tag used in the answer, e.g. [doc1]")
    source: Source = Field(..., description="The source document details")


class ChatResponse(BaseModel):
    """Response body from the POST /chat endpoint."""

    answer: str = Field(..., description="The grounded answer with inline citations")
    citations: list[Citation] = Field(
        default_factory=list, description="List of cited sources"
    )
    retrieval_count: int = Field(
        0, description="Number of chunks retrieved from the index"
    )
    model: str = Field("", description="Model deployment used for generation")
