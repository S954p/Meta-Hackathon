from __future__ import annotations

import pytest

from support_env.environment import SupportTicketEnvironment
from support_env.grader import grade_episode


def test_reset_returns_valid_observation():
    env = SupportTicketEnvironment()
    obs = env.reset(task_id="easy_password_reset", seed=1)
    assert obs.episode_id
    assert obs.ticket_id
    assert obs.customer_message
    assert obs.ticket_status == "OPEN"
    assert 0.0 <= obs.customer_satisfaction_score <= 1.0


def test_step_classify_reward_and_transition():
    env = SupportTicketEnvironment()
    env.reset(task_id="easy_password_reset", seed=1)

    obs, reward, done, info = env.step({"action_type": "classify_ticket", "action_input": {"issue_type": "password_reset"}})
    assert done is False
    assert obs.ticket_status == "IN_PROGRESS"
    # Per-step + SLA penalties are folded into reward_score (immediate − penalties).
    assert reward.reward_score == pytest.approx(0.2 - SupportTicketEnvironment._STEP_PENALTY, abs=1e-3)
    assert info["ticket_status"] == "IN_PROGRESS"


def test_invalid_actions_handling():
    env = SupportTicketEnvironment()
    env.reset(task_id="easy_password_reset", seed=1)

    obs, reward, done, info = env.step({"action_type": "not_a_real_action", "action_input": {}})
    assert done is False
    assert reward.reward_score == 0.0
    assert info["invalid_reason"] or "invalid_reason" in info


def test_episode_termination_on_close():
    env = SupportTicketEnvironment()
    env.reset(task_id="easy_password_reset", seed=1)

    actions = [
        {"action_type": "classify_ticket", "action_input": {"issue_type": "password_reset"}},
        {"action_type": "search_knowledge_base", "action_input": {"query": "forgot password reset link"}},
        {
            "action_type": "send_response",
            "action_input": {"response": "To reset your password, click 'Forgot password' and use the reset link to set a new password."},
        },
        {"action_type": "confirm_customer_resolution", "action_input": {"customer_note": "Thanks, that works."}},
        {"action_type": "resolve_ticket", "action_input": {"resolution_summary": "Provided reset link and new password steps."}},
        {"action_type": "close_ticket", "action_input": {}},
    ]

    done = False
    for a in actions:
        obs, reward, done, info = env.step(a)
        if done:
            break

    assert done is True
    assert obs.ticket_status == "CLOSED"
    assert env.state().ticket.status == "CLOSED"


def test_grader_scoring_correctness_easy():
    env = SupportTicketEnvironment()
    env.reset(task_id="easy_password_reset", seed=1)

    actions = [
        {"action_type": "classify_ticket", "action_input": {"issue_type": "password_reset"}},
        {"action_type": "search_knowledge_base", "action_input": {"query": "forgot password reset link"}},
        {
            "action_type": "send_response",
            "action_input": {
                "response": (
                    "To reset your password: go to the sign-in page, click 'Forgot password', enter your email, "
                    "and use the reset link from your inbox to set a new password."
                )
            },
        },
        {"action_type": "confirm_customer_resolution", "action_input": {"customer_note": "Thanks."}},
        {"action_type": "resolve_ticket", "action_input": {"resolution_summary": "Reset your password using the reset link and set a new password."}},
        {"action_type": "close_ticket", "action_input": {}},
    ]

    done = False
    for a in actions:
        _, _, done, _ = env.step(a)
        if done:
            break

    score = grade_episode(env.state())
    assert score == pytest.approx(1.0, abs=1e-6)

