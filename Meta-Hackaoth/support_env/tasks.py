from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from .models import CustomerScenario, IssueType, TicketPriority


TaskId = Literal["easy_password_reset", "medium_billing_missing_info", "hard_technical_troubleshooting"]


@dataclass(frozen=True)
class TaskSpec:
    task_id: TaskId
    expected_issue_type: IssueType
    initial_customer_message: str
    default_priority: TicketPriority
    sla_seconds: float
    max_steps: int

    # Minimal “optimal” number of steps to complete the workflow.
    optimal_steps: int

    # Expected minimum workflow elements (used by deterministic grader + reward).
    requires_kb_search_count_at_least: int
    requires_questions_count_at_least: int

    # For “missing info” tasks (medium): required requested_info key(s).
    required_requested_info_keys: List[str]

    # For “troubleshooting flow” tasks (hard): keywords that must appear in send_response.
    send_response_must_include_keywords: List[str]

    # Workflow actions required (supports duplicate steps for hard tasks).
    required_actions: List[str]


TASKS: Dict[TaskId, TaskSpec] = {
    "easy_password_reset": TaskSpec(
        task_id="easy_password_reset",
        expected_issue_type="password_reset",
        initial_customer_message=(
            "Hi, I can't log in. When I try to reset my password, nothing happens. "
            "Please help me regain access."
        ),
        default_priority="LOW",
        sla_seconds=10 * 60,
        max_steps=8,
        optimal_steps=6,
        requires_kb_search_count_at_least=1,
        requires_questions_count_at_least=0,
        required_requested_info_keys=[],
        send_response_must_include_keywords=["forgot password", "reset your password", "reset link", "new password"],
        required_actions=[
            "classify_ticket",
            "search_knowledge_base",
            "send_response",
            "confirm_customer_resolution",
            "resolve_ticket",
            "close_ticket",
        ],
    ),
    "medium_billing_missing_info": TaskSpec(
        task_id="medium_billing_missing_info",
        expected_issue_type="billing_double_charge_missing_info",
        initial_customer_message=(
            "Hello, I was charged twice for the same subscription this month. "
            "I need this fixed, but I don't know what details billing needs."
        ),
        default_priority="MEDIUM",
        sla_seconds=20 * 60,
        max_steps=10,
        optimal_steps=7,
        requires_kb_search_count_at_least=1,
        requires_questions_count_at_least=1,
        required_requested_info_keys=["invoice_number"],
        send_response_must_include_keywords=["refund", "duplicate", "invoice", "billing month"],
        required_actions=[
            "classify_ticket",
            "ask_customer_question",
            "search_knowledge_base",
            "send_response",
            "confirm_customer_resolution",
            "resolve_ticket",
            "close_ticket",
        ],
    ),
    "hard_technical_troubleshooting": TaskSpec(
        task_id="hard_technical_troubleshooting",
        expected_issue_type="technical_wifi_disconnect_troubleshooting",
        initial_customer_message=(
            "After the last app update, my Wi-Fi keeps disconnecting every few minutes. "
            "It reconnects sometimes but gets unstable."
        ),
        default_priority="HIGH",
        sla_seconds=30 * 60,
        max_steps=14,
        optimal_steps=9,
        requires_kb_search_count_at_least=1,
        requires_questions_count_at_least=2,
        required_requested_info_keys=[],
        send_response_must_include_keywords=["forget the network", "power-cycle", "router firmware", "DNS", "switch band"],
        required_actions=[
            "classify_ticket",
            "ask_customer_question",
            "ask_customer_question",
            "search_knowledge_base",
            "send_response",
            "confirm_customer_resolution",
            "resolve_ticket",
            "close_ticket",
        ],
    ),
}


def get_task(task_id: TaskId) -> TaskSpec:
    return TASKS[task_id]


def _maybe_angry_prefix(scenario: CustomerScenario, text: str) -> str:
    if scenario != "angry_customer" or not text.strip():
        return text
    return f"I'm frustrated — {text}"


def deterministic_customer_response(
    task_id: TaskId,
    question_type: str,
    requested_info_key: Optional[str] = None,
    *,
    turn_index: int = 0,
    scenario: CustomerScenario = "cooperative",
    silent_attempt: int = 0,
) -> str:
    """
    Deterministic responses to ensure reproducible environment behavior.
    `silent_customer`: first two ask attempts yield empty replies (agent must follow up).
    `angry_customer`: negative tone prefix on replies.
    """
    if scenario == "silent_customer" and silent_attempt < 2:
        return ""

    if task_id == "medium_billing_missing_info":
        if requested_info_key == "invoice_number":
            out = "Sure — my invoice number is INV-20491 for the billing month of April."
            return _maybe_angry_prefix(scenario, out)
        out = "Please share the required billing details."
        return _maybe_angry_prefix(scenario, out)

    if task_id == "hard_technical_troubleshooting":
        q = (question_type or "").lower()
        tone = "Thanks for checking — " if turn_index % 2 == 1 else ""
        if "router_firmware" in q or "firmware" in q:
            out = f"{tone}Router firmware was updated last night (version 1.2.3)."
            return _maybe_angry_prefix(scenario, out)
        if "dns" in q:
            out = f"{tone}DNS is currently set to manual (8.8.8.8 and 8.8.4.4)."
            return _maybe_angry_prefix(scenario, out)
        if "band" in q:
            out = f"{tone}Most of the time I'm on 5GHz, but it sometimes switches."
            return _maybe_angry_prefix(scenario, out)
        if "device" in q or "model" in q:
            out = f"{tone}I'm using a TP-Link Archer AX55."
            return _maybe_angry_prefix(scenario, out)
        if "error" in q or "logs" in q:
            out = f"{tone}No clear error logs — it just drops and reconnects."
            return _maybe_angry_prefix(scenario, out)
        out = f"{tone}I can check that for you."
        return _maybe_angry_prefix(scenario, out)

    # No “customer Q&A” needed in easy.
    out = "Thanks — please proceed."
    return _maybe_angry_prefix(scenario, out)

