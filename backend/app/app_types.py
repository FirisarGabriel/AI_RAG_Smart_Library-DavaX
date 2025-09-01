
"""
Pydantic models (DTOs) for request/response in Smart Library backend.

These models:
- Define the contract between backend and frontend.
- Are mirrored by TypeScript types in frontend/src/lib/types.ts
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


# -----------------------------
# Request DTOs
# -----------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message or query text.")


# -----------------------------
# Streaming chunks (SSE events)
# -----------------------------

class StreamChunk(BaseModel):
    type: str = Field(..., description="Event type: 'token' | 'final' | 'error'")
    text: Optional[str] = Field(None, description="Delta text when type=='token'.")
    error: Optional[str] = Field(None, description="Error message if type=='error'.")


# -----------------------------
# Final response payload
# -----------------------------

class FinalResponse(BaseModel):
    final: bool = Field(True, description="Always true for final payloads.")
    recommendation: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured info about recommended book (title, why). Optional.",
    )
    summary: Optional[str] = Field(
        None, description="Full summary returned by the tool for the recommended book."
    )
