from __future__ import annotations

"""
Deterministic, task-specific programmatic graders (benchmark contract).

Each function takes a GradingView (derived from EnvironmentState only).
"""

from .grading_view import GradingView


def grade_password_reset(view: GradingView) -> float:
    """
    Full credit: ticket closed after using matched KB articles.
    (Strict success signal for the easy password-reset task.)
    """
    if view.ticket_status == "CLOSED" and view.used_kb:
        return 1.0
    return 0.0


def grade_billing(view: GradingView) -> float:
    """
    Full credit: refund path articulated and invoice evidence collected.
    Partial credit: episode progressed but verification incomplete.
    """
    if view.refund_issued and view.invoice_verified:
        return 1.0
    return 0.5


def grade_technical(view: GradingView) -> float:
    """
    Full credit: sufficient troubleshooting coverage and clean close.
    Partial: default floor when the rubric is not fully met (typical mid-episode).
    """
    if view.troubleshooting_steps >= 3 and view.ticket_status == "CLOSED":
        return 1.0
    return 0.6


def grade_from_view(view: GradingView) -> float:
    """Dispatch by task id."""
    if view.task_id == "easy_password_reset":
        return grade_password_reset(view)
    if view.task_id == "medium_billing_missing_info":
        return grade_billing(view)
    if view.task_id == "hard_technical_troubleshooting":
        return grade_technical(view)
    return 0.0
