from __future__ import annotations

from support_env.grading_view import GradingView
from support_env.task_graders import grade_billing, grade_password_reset, grade_technical


def test_grade_password_reset_binary():
    assert grade_password_reset(GradingView("easy_password_reset", "CLOSED", True, True, False, False, 0, False)) == 1.0
    assert grade_password_reset(GradingView("easy_password_reset", "CLOSED", False, True, False, False, 0, False)) == 0.0
    assert grade_password_reset(GradingView("easy_password_reset", "RESOLVED", True, True, False, False, 0, False)) == 0.0


def test_grade_billing_partial():
    assert grade_billing(GradingView("medium_billing_missing_info", "CLOSED", True, True, True, True, 0, False)) == 1.0
    assert grade_billing(GradingView("medium_billing_missing_info", "OPEN", True, True, False, True, 0, False)) == 0.5


def test_grade_technical_floor():
    assert grade_technical(GradingView("hard_technical_troubleshooting", "CLOSED", True, True, False, False, 4, False)) == 1.0
    assert grade_technical(GradingView("hard_technical_troubleshooting", "CLOSED", True, True, False, False, 2, False)) == 0.6
    assert grade_technical(GradingView("hard_technical_troubleshooting", "IN_PROGRESS", True, True, False, False, 5, False)) == 0.6
