from __future__ import annotations

from typing import Dict, List

from .tasks import TaskId


WORKFLOW_POLICY: Dict[TaskId, List[str]] = {
    "easy_password_reset": [
        "classify_ticket",
        "search_knowledge_base",
        "send_response",
        "confirm_customer_resolution",
        "resolve_ticket",
        "close_ticket",
    ],
    "medium_billing_missing_info": [
        "classify_ticket",
        "ask_customer_question",
        "search_knowledge_base",
        "send_response",
        "confirm_customer_resolution",
        "resolve_ticket",
        "close_ticket",
    ],
    "hard_technical_troubleshooting": [
        "classify_ticket",
        "ask_customer_question",
        "ask_customer_question",
        "search_knowledge_base",
        "send_response",
        "confirm_customer_resolution",
        "resolve_ticket",
        "close_ticket",
    ],
}


def workflow_for_task(task_id: TaskId) -> List[str]:
    return list(WORKFLOW_POLICY[task_id])

