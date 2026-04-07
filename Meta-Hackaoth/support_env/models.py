from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


TicketStatus = Literal[
    "OPEN",
    "IN_PROGRESS",
    "WAITING_FOR_CUSTOMER",
    "WAITING_FOR_CONFIRMATION",
    "RESOLVED",
    "CLOSED",
    "REOPENED",
    "ESCALATED",
]
TicketPriority = Literal["LOW", "MEDIUM", "HIGH"]

IssueType = Literal[
    "password_reset",
    "billing_double_charge_missing_info",
    "technical_wifi_disconnect_troubleshooting",
]

ActionType = Literal[
    "classify_ticket",
    "ask_customer_question",
    "search_knowledge_base",
    "send_response",
    "confirm_customer_resolution",
    "resolve_ticket",
    "close_ticket",
    "reopen_ticket",
    "escalate_ticket",
    "update_ticket_priority",
]

CustomerScenario = Literal["cooperative", "angry_customer", "silent_customer", "escalation_hint"]


class KnowledgeBaseResult(BaseModel):
    query: str
    kb_topic: str
    matched: bool = False
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Heuristic retrieval score")
    articles: List[str] = Field(default_factory=list)


class Ticket(BaseModel):
    ticket_id: str
    status: TicketStatus = "OPEN"
    priority: TicketPriority = "MEDIUM"
    issue_type: Optional[IssueType] = None
    resolution_notes: Optional[str] = None


class Customer(BaseModel):
    customer_id: str
    customer_message: str = ""
    customer_satisfaction_score: float = 0.5
    last_customer_response: Optional[str] = None
    scenario: CustomerScenario = Field(
        default="cooperative",
        description="Customer simulation profile (failure / stress modes for benchmarking).",
    )


class ActionRecord(BaseModel):
    action_type: ActionType
    action_input: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    step_count: int = 0
    last_action_type: Optional[ActionType] = None
    actions_taken: List[ActionRecord] = Field(default_factory=list)
    seen_kb_queries: List[str] = Field(default_factory=list)
    requested_info: Dict[str, str] = Field(default_factory=dict)
    diagnostic_answers: Dict[str, str] = Field(default_factory=dict)
    knowledge_base_results: List[KnowledgeBaseResult] = Field(default_factory=list)


class EnvironmentState(BaseModel):
    episode_id: str
    task_id: str
    time_elapsed_seconds: float
    step_count: int
    ticket: Ticket
    customer: Customer
    agent_state: AgentState
    done: bool = False
    episode_timeline: List[Dict[str, Any]] = Field(default_factory=list)


class Observation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    episode_id: str = Field(default="", description="Unique episode identifier.")
    ticket_id: str = Field(..., description="Support ticket id shown to the agent.")
    customer_message: str = Field(..., description="Latest customer-visible message.")
    ticket_status: TicketStatus
    ticket_priority: TicketPriority
    conversation_history: List[str] = Field(
        default_factory=list,
        description="Ordered transcript (prefix Customer:/Agent: lines).",
    )
    knowledge_base_results: List[KnowledgeBaseResult] = Field(default_factory=list)
    time_elapsed: float = Field(..., description="Simulated seconds elapsed in-episode.")
    actions_taken: List[ActionType] = Field(default_factory=list)
    customer_satisfaction_score: float = Field(..., ge=0.0, le=1.0)
    scenario: CustomerScenario = Field(
        default="cooperative",
        description="Active customer simulation scenario for this episode.",
    )


class Action(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_type: ActionType = Field(..., description="Environment step verb.")
    action_input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured payload; keys depend on action_type (see OpenEnv / server docs).",
    )


class Reward(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reward_score: float = Field(..., ge=0.0, le=1.0, description="Shaped scalar for this step.")
    progress_score: float = Field(..., ge=0.0, le=1.0)
    penalty_score: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(default="", description="Human-readable transition note.")


class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class StateResponse(BaseModel):
    state: EnvironmentState

