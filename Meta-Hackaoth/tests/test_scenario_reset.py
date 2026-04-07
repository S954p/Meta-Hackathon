from __future__ import annotations

from support_env.environment import SupportTicketEnvironment


def test_reset_scenario_escalation_hint_in_message():
    env = SupportTicketEnvironment()
    obs = env.reset(task_id="easy_password_reset", seed=0, scenario="escalation_hint")
    assert obs.scenario == "escalation_hint"
    assert "supervisor" in obs.customer_message.lower()


def test_reset_scenario_silent_customer():
    env = SupportTicketEnvironment()
    env.reset(task_id="medium_billing_missing_info", seed=1, scenario="silent_customer")
    _, _, done, _ = env.step(
        {
            "action_type": "classify_ticket",
            "action_input": {"issue_type": "billing_double_charge_missing_info"},
        }
    )
    assert not done
    obs2, _, _, _ = env.step(
        {
            "action_type": "ask_customer_question",
            "action_input": {
                "question_type": "billing",
                "question": "Invoice please?",
                "requested_info_key": "invoice_number",
            },
        }
    )
    transcript = "\n".join(obs2.conversation_history)
    assert "No response yet" in transcript, transcript
