from __future__ import annotations

"""
Typed Pydantic payloads for each `action_type` (reference / validation helpers).

Runtime stepping still accepts `Action` with a generic `action_input` dict; clients may
validate payloads with these models before sending.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ClassifyTicketInput(BaseModel):
    issue_type: str = Field(..., description="Expected issue slug, e.g. password_reset")
    predicted_issue_type: Optional[str] = Field(default=None)


class AskCustomerInput(BaseModel):
    question_type: str = ""
    question: str = ""
    requested_info_key: Optional[str] = None


class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., min_length=1)
    q: Optional[str] = None


class SendResponseInput(BaseModel):
    response: str = Field(..., min_length=1)
    message: Optional[str] = None
    text: Optional[str] = None


class ConfirmResolutionInput(BaseModel):
    customer_note: str = ""


class ResolveTicketInput(BaseModel):
    resolution_summary: str = ""
    resolution_notes: Optional[str] = None


class CloseTicketInput(BaseModel):
    pass


class ReopenTicketInput(BaseModel):
    reason: str = ""
    customer_note: Optional[str] = None


class EscalateTicketInput(BaseModel):
    reason: str = Field(..., min_length=1)


class UpdatePriorityInput(BaseModel):
    priority: Literal["LOW", "MEDIUM", "HIGH"]
