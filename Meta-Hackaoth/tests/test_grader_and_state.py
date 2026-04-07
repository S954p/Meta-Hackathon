from __future__ import annotations

import pytest

from support_env.environment import SupportTicketEnvironment
from support_env.grader import grade_episode


def run_task(env: SupportTicketEnvironment, task_id: str, actions):
    env.reset(task_id=task_id, seed=1)
    done = False
    for a in actions:
        _, _, done, _ = env.step(a)
        if done:
            break
    return done


def test_state_returns_environment_state():
    env = SupportTicketEnvironment()
    env.reset(task_id="easy_password_reset", seed=1)
    state = env.state()
    assert state.episode_id
    assert state.task_id == "easy_password_reset"
    assert state.ticket.ticket_id
    assert state.customer.customer_message
    assert state.agent_state.step_count == 0


def test_grader_scoring_correctness_medium():
    env = SupportTicketEnvironment()
    actions = [
        {"action_type": "classify_ticket", "action_input": {"issue_type": "billing_double_charge_missing_info"}},
        {
            "action_type": "ask_customer_question",
            "action_input": {
                "question_type": "billing",
                "question": "Can you share the invoice number for the duplicate charge?",
                "requested_info_key": "invoice_number",
            },
        },
        {"action_type": "search_knowledge_base", "action_input": {"query": "double charge invoice refund duplicate"}},
        {"action_type": "send_response", "action_input": {"response": "We'll investigate the duplicate charge and process a refund using your invoice number for the billing month."}},
        {"action_type": "confirm_customer_resolution", "action_input": {"customer_note": "OK, proceed."}},
        {"action_type": "resolve_ticket", "action_input": {"resolution_summary": "Confirmed duplicate billing capture using invoice and issued a refund for the billing month."}},
        {"action_type": "close_ticket", "action_input": {}},
    ]
    done = run_task(env, "medium_billing_missing_info", actions)
    assert done is True
    assert env.state().ticket.status == "CLOSED"
    assert grade_episode(env.state()) == pytest.approx(1.0, abs=1e-6)


def test_grader_scoring_correctness_hard():
    env = SupportTicketEnvironment()
    actions = [
        {"action_type": "classify_ticket", "action_input": {"issue_type": "technical_wifi_disconnect_troubleshooting"}},
        {"action_type": "ask_customer_question", "action_input": {"question_type": "dns_settings", "question": "What are your DNS settings?"}},
        {
            "action_type": "ask_customer_question",
            "action_input": {"question_type": "router_firmware", "question": "Have you updated router firmware recently?"},
        },
        {"action_type": "search_knowledge_base", "action_input": {"query": "wifi disconnect forget network power-cycle router firmware DNS switch band"}},
        {"action_type": "send_response", "action_input": {"response": "Forget the network and reconnect; power-cycle the router; check router firmware; verify DNS; switch band (2.4GHz vs 5GHz)."}},
        {"action_type": "confirm_customer_resolution", "action_input": {"customer_note": "Will try these steps."}},
        {"action_type": "resolve_ticket", "action_input": {"resolution_summary": "Provided Wi-Fi disconnect troubleshooting: forget network, power-cycle router, verify firmware, update DNS, and switch band."}},
        {"action_type": "close_ticket", "action_input": {}},
    ]
    done = run_task(env, "hard_technical_troubleshooting", actions)
    assert done is True
    assert env.state().ticket.status == "CLOSED"
    assert grade_episode(env.state()) == pytest.approx(1.0, abs=1e-6)

