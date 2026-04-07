from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Set

from .models import EnvironmentState
from .tasks import get_task


def _lower(s: str) -> str:
    return (s or "").lower()


def _get_action_issue_type(action_input: Dict[str, Any]) -> str:
    for key in ("issue_type", "predicted_issue_type", "classification", "category"):
        v = action_input.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _get_action_text(action_input: Dict[str, Any]) -> str:
    for key in ("response", "resolution_summary", "resolution_notes", "message", "question", "text"):
        v = action_input.get(key)
        if isinstance(v, str):
            return v
    if isinstance(action_input.get("content"), str):
        return action_input["content"]
    return ""


def _get_requested_info_key(action_input: Dict[str, Any]) -> str:
    for key in ("requested_info_key", "requested_info", "info_key", "missing_info_key"):
        v = action_input.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


@dataclass(frozen=True)
class GradingView:
    """
    Read-only signals for programmatic per-task graders (benchmark-style).
    Built purely from `EnvironmentState` — no private env fields.
    """

    task_id: str
    ticket_status: str
    used_kb: bool
    correct_classification: bool
    refund_issued: bool
    invoice_verified: bool
    troubleshooting_steps: int
    escalated: bool


def build_grading_view(state: EnvironmentState) -> GradingView:
    task = get_task(state.task_id)  # type: ignore[arg-type]
    actions = state.agent_state.actions_taken

    classify_actions = [a for a in actions if a.action_type == "classify_ticket"]
    kb_actions = [a for a in actions if a.action_type == "search_knowledge_base"]
    ask_actions = [a for a in actions if a.action_type == "ask_customer_question"]
    send_actions = [a for a in actions if a.action_type == "send_response"]
    resolve_actions = [a for a in actions if a.action_type == "resolve_ticket"]
    close_actions = [a for a in actions if a.action_type == "close_ticket"]

    classify_issue = _get_action_issue_type(classify_actions[-1].action_input) if classify_actions else ""
    send_text = _get_action_text(send_actions[-1].action_input) if send_actions else ""
    resolve_text = _get_action_text(resolve_actions[-1].action_input) if resolve_actions else ""
    combined_agent_text = _lower(send_text + " " + resolve_text)

    knowledge_used = len(state.agent_state.knowledge_base_results) > 0 and sum(
        1 for r in state.agent_state.knowledge_base_results if r.matched
    ) >= 1
    used_kb = len(kb_actions) >= task.requires_kb_search_count_at_least and knowledge_used

    correct_classification = classify_issue == task.expected_issue_type

    # Billing: invoice collected via ask flow + refund language in resolution path
    asked_invoice = any(_get_requested_info_key(a.action_input) == "invoice_number" for a in ask_actions)
    inv_val = (state.agent_state.requested_info.get("invoice_number") or "").strip()
    invoice_verified = asked_invoice and bool(re.search(r"INV-?\d+", inv_val, re.I))
    refund_issued = "refund" in combined_agent_text and ("invoice" in combined_agent_text or "duplicate" in combined_agent_text)

    # Technical: distinct diagnostics + KB-aligned troubleshooting anchors in agent text
    distinct_q: Set[str] = set()
    for a in ask_actions:
        inp = a.action_input if isinstance(a.action_input, dict) else {}
        qt = ""
        for key in ("question_type", "diagnostic_key", "topic", "type"):
            if isinstance(inp.get(key), str) and inp[key].strip():
                qt = inp[key].strip()
                break
        if qt:
            distinct_q.add(qt)
    keyword_hits = sum(1 for kw in task.send_response_must_include_keywords if _lower(kw) in combined_agent_text)
    troubleshooting_steps = len(distinct_q) + keyword_hits

    escalated = state.ticket.status == "ESCALATED" or any(a.action_type == "escalate_ticket" for a in actions)
    ticket_status = state.ticket.status

    # used_kb read as "matched KB used" for password grader consistency
    _ = close_actions  # reserved if graders need strict close-action check later

    return GradingView(
        task_id=state.task_id,
        ticket_status=ticket_status,
        used_kb=used_kb,
        correct_classification=correct_classification,
        refund_issued=refund_issued,
        invoice_verified=invoice_verified,
        troubleshooting_steps=troubleshooting_steps,
        escalated=escalated,
    )
