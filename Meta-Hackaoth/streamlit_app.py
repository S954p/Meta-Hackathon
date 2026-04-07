from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from streamlit_command_center import main as _command_center_main

# Render the next-generation command center UI and stop executing the legacy code.
_command_center_main()
st.stop()


def _get_backend_base_url() -> str:
    """
    Resolve backend URL without crashing when secrets.toml is missing.
    Priority:
    1) BACKEND_BASE_URL environment variable
    2) Streamlit secrets BACKEND_BASE_URL (if available)
    3) localhost default
    """
    env_url = os.getenv("BACKEND_BASE_URL")
    if env_url:
        return env_url

    try:
        secret_url = st.secrets.get("BACKEND_BASE_URL", None)
        if secret_url:
            return str(secret_url)
    except StreamlitSecretNotFoundError:
        # No secrets.toml configured; fallback safely.
        pass
    except Exception:
        # Any secrets parsing issue should not break app startup.
        pass

    return "http://localhost:8000"


BACKEND_BASE_URL = _get_backend_base_url()


TASK_LABELS = {
    "easy_password_reset": "Easy - Password Reset",
    "medium_billing_missing_info": "Medium - Billing Issue",
    "hard_technical_troubleshooting": "Hard - Technical Issue",
}


ACTION_TYPES = [
    "classify_ticket",
    "ask_customer_question",
    "search_knowledge_base",
    "send_response",
    "resolve_ticket",
    "close_ticket",
    "escalate_ticket",
    "update_ticket_priority",
]


DEFAULT_ACTION_INPUTS: Dict[str, Dict[str, Any]] = {
    "classify_ticket": {"issue_type": "password_reset"},
    "ask_customer_question": {"question_type": "billing", "question": "Can you share the invoice number?", "requested_info_key": "invoice_number"},
    "search_knowledge_base": {"query": "forgot password reset link"},
    "send_response": {"response": "Please follow the steps below to resolve your issue."},
    "resolve_ticket": {"resolution_summary": "Resolution summary goes here."},
    "close_ticket": {},
    "escalate_ticket": {"reason": "Escalating for specialist review."},
    "update_ticket_priority": {"priority": "HIGH"},
}


STATUS_COLORS = {
    "OPEN": "#2E86DE",  # blue
    "IN_PROGRESS": "#F5A623",  # orange
    "WAITING_FOR_CUSTOMER": "#F5A623",  # orange
    "RESOLVED": "#2ECC71",  # green
    "CLOSED": "#7F8C8D",  # grey
    "ESCALATED": "#E74C3C",  # red
}


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#95A5A6")
    return f"""
<span style="
  display:inline-block;
  padding:4px 10px;
  border-radius:999px;
  background:{color};
  color:white;
  font-weight:600;
  font-size:12px;">
{status}
</span>
"""


def call_backend(method: str, path: str, json_payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    url = f"{BACKEND_BASE_URL}{path}"
    r = requests.request(method=method, url=url, json=json_payload, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def pretty_json(text: str) -> Optional[dict]:
    text = (text or "").strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Action input JSON must be an object/dictionary.")
    return parsed


st.set_page_config(page_title="Customer Support Agent Console", layout="wide")

st.title("Customer Support Ticket Resolution Dashboard")
st.caption(f"Connected to backend: `{BACKEND_BASE_URL}`")


if "episode_id" not in st.session_state:
    st.session_state.episode_id = None
if "task_id" not in st.session_state:
    st.session_state.task_id = "easy_password_reset"
if "observation" not in st.session_state:
    st.session_state.observation = None
if "reward" not in st.session_state:
    st.session_state.reward = None
if "done" not in st.session_state:
    st.session_state.done = False
if "steps_taken" not in st.session_state:
    st.session_state.steps_taken = 0
if "actions_history" not in st.session_state:
    st.session_state.actions_history = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "action_type" not in st.session_state:
    st.session_state.action_type = "classify_ticket"
if "action_input_text" not in st.session_state:
    st.session_state.action_input_text = json.dumps(DEFAULT_ACTION_INPUTS["classify_ticket"], indent=2)
if "tasks_meta" not in st.session_state:
    st.session_state.tasks_meta = []


def sync_action_input_defaults() -> None:
    if st.session_state.action_type in DEFAULT_ACTION_INPUTS:
        st.session_state.action_input_text = json.dumps(DEFAULT_ACTION_INPUTS[st.session_state.action_type], indent=2)


def refresh_state() -> None:
    if not st.session_state.episode_id:
        return
    payload = call_backend("GET", "/state", params={"episode_id": st.session_state.episode_id}).get("state", {})
    ticket = payload.get("ticket", {}) or {}
    customer = payload.get("customer", {}) or {}
    agent_state = payload.get("agent_state", {}) or {}
    st.session_state.observation = {
        "ticket_id": ticket.get("ticket_id", ""),
        "customer_message": customer.get("customer_message", ""),
        "ticket_status": ticket.get("status", ""),
        "ticket_priority": ticket.get("priority", ""),
        "conversation_history": [str(x) for x in agent_state.get("actions_taken", [])] if False else st.session_state.observation.get("conversation_history", []) if st.session_state.observation else [],
        "knowledge_base_results": agent_state.get("knowledge_base_results", []),
        "time_elapsed": payload.get("time_elapsed_seconds", 0.0),
        "actions_taken": [a.get("action_type", "") for a in agent_state.get("actions_taken", []) if isinstance(a, dict)],
        "customer_satisfaction_score": customer.get("customer_satisfaction_score", 0.0),
    }
    st.session_state.done = bool(payload.get("done", False))
    st.session_state.steps_taken = int(payload.get("step_count", st.session_state.steps_taken))


left, center, right = st.columns([0.28, 0.44, 0.28], gap="large")


with left:
    st.subheader("Controls")
    chosen_task_label = st.selectbox(
        "Select task",
        options=list(TASK_LABELS.keys()),
        format_func=lambda k: TASK_LABELS[k],
        index=list(TASK_LABELS.keys()).index(st.session_state.task_id) if st.session_state.task_id in TASK_LABELS else 0,
    )
    st.session_state.task_id = chosen_task_label

    seed = st.number_input("Seed (deterministic episodes)", min_value=0, max_value=2**31 - 1, value=123, step=1)

    if st.button("Reset Environment", type="primary"):
        try:
            with st.spinner("Resetting episode..."):
                resp = call_backend("POST", "/reset", json_payload={"task_id": st.session_state.task_id, "seed": int(seed)})
            st.session_state.episode_id = resp["episode_id"]
            st.session_state.observation = resp.get("observation")
            st.session_state.reward = None
            st.session_state.done = resp.get("done", False)
            st.session_state.steps_taken = 0
            st.session_state.actions_history = []
            st.session_state.logs = []

            st.success(f"Episode started for `{st.session_state.task_id}`")
        except requests.RequestException as e:
            st.error(f"Reset failed: {e}")

    st.divider()

    # Ticket information
    st.subheader("Ticket Information")
    obs = st.session_state.observation or {}
    ticket_id = obs.get("ticket_id", "—")
    customer_message = obs.get("customer_message", "")
    ticket_status = obs.get("ticket_status", "—")
    ticket_priority = obs.get("ticket_priority", "—")
    time_elapsed = float(obs.get("time_elapsed", 0.0) or 0.0)

    if not st.session_state.tasks_meta:
        try:
            with st.spinner("Loading tasks metadata..."):
                st.session_state.tasks_meta = call_backend("GET", "/tasks").get("tasks", [])
        except requests.RequestException:
            st.session_state.tasks_meta = []
    tasks_meta = st.session_state.tasks_meta

    task_spec = next((t for t in tasks_meta if t.get("task_id") == st.session_state.task_id), None)
    sla_seconds = float(task_spec.get("sla_seconds")) if task_spec else 0.0
    max_steps = int(task_spec.get("max_steps")) if task_spec else 0
    remaining_sla = max(0.0, sla_seconds - time_elapsed)

    st.markdown(status_badge(ticket_status) if ticket_status != "—" else "—", unsafe_allow_html=True)
    st.caption(f"Ticket ID: `{ticket_id}`")
    st.caption(f"Priority: `{ticket_priority}`")
    st.caption(f"Time Elapsed: `{time_elapsed:.0f}s`")
    if task_spec:
        st.caption(f"SLA Deadline: `{remaining_sla:.0f}s remaining`")

    st.caption(f"Episode Status: `{ 'FINISHED' if st.session_state.done else 'RUNNING' }`")
    if max_steps:
        st.progress(min(1.0, st.session_state.steps_taken / max_steps))

    if st.session_state.reward is not None:
        st.caption(f"Last Reward (final step): `{st.session_state.reward.get('reward_score', 0.0):.2f}`")
        st.caption(f"Progress Score: `{st.session_state.reward.get('progress_score', 0.0):.2f}`")

    st.subheader("Episode Progress")
    st.metric("Steps Taken", st.session_state.steps_taken)
    if max_steps:
        st.metric("Max Steps", max_steps)


with center:
    st.subheader("Customer Message")
    if st.session_state.observation:
        st.info(customer_message)
    else:
        st.warning("Reset the environment to load a ticket.")

    st.divider()

    st.subheader("Conversation History")
    if st.session_state.observation:
        convo = st.session_state.observation.get("conversation_history", []) or []
        if convo:
            for msg in convo:
                if msg.startswith("Customer:"):
                    st.chat_message("user").write(msg.replace("Customer:", "").strip())
                elif msg.startswith("Agent:") or msg.startswith("Agent: Resolution"):
                    st.chat_message("assistant").write(msg.replace("Agent:", "").strip())
                else:
                    st.chat_message("assistant").write(msg)
        else:
            st.caption("No conversation yet.")

    st.divider()

    st.subheader("Knowledge Base Results")
    if st.session_state.observation:
        kb_results = st.session_state.observation.get("knowledge_base_results", []) or []
        if kb_results:
            for res in kb_results:
                query = res.get("query", "")
                kb_topic = res.get("kb_topic", "")
                matched = bool(res.get("matched", False))
                confidence = 0.9 if matched else 0.4
                st.markdown(f"**Topic:** `{kb_topic}`  \n**Confidence:** `{confidence:.2f}`")
                articles = res.get("articles", []) or []
                # articles is stored as free-form title/body text in this deterministic implementation
                for a in articles:
                    st.caption(a.splitlines()[0] if a else "")
                    st.write(a)
                st.divider()
        else:
            st.caption("No KB results yet.")


with right:
    st.subheader("Agent Actions")
    if not st.session_state.episode_id:
        st.warning("Start an episode by clicking Reset.")
    elif st.session_state.done:
        st.error("Episode finished. Reset to start a new ticket.")
    else:
        if "last_action_type" not in st.session_state:
            st.session_state.last_action_type = st.session_state.action_type
        action_type = st.selectbox(
            "Action type",
            ACTION_TYPES,
            index=ACTION_TYPES.index(st.session_state.action_type) if st.session_state.action_type in ACTION_TYPES else 0,
            key="action_type",
        )
        if st.session_state.last_action_type != action_type:
            st.session_state.action_type = action_type
            sync_action_input_defaults()
            st.session_state.last_action_type = action_type

        action_input_text = st.text_area(
            "Action input (JSON)",
            value=st.session_state.action_input_text,
            height=160,
            key="action_input_text",
        )

        if st.button("Send Action Step", type="primary"):
            if not st.session_state.episode_id:
                st.error("No active episode.")
            else:
                try:
                    parsed_action_input = pretty_json(action_input_text)
                    if parsed_action_input is None:
                        parsed_action_input = {}
                    action_payload = {"action_type": st.session_state.action_type, "action_input": parsed_action_input}

                    with st.spinner("Stepping environment..."):
                        resp = call_backend(
                            "POST",
                            "/step",
                            json_payload={"episode_id": st.session_state.episode_id, "action": action_payload},
                        )

                    st.session_state.observation = resp.get("observation")
                    st.session_state.reward = resp.get("reward")
                    st.session_state.done = bool(resp.get("done", False))
                    st.session_state.steps_taken += 1

                    info = resp.get("info", {}) or {}
                    reason = st.session_state.reward.get("reason", "") if st.session_state.reward else ""
                    st.session_state.actions_history.append(
                        {
                            "action_type": action_payload["action_type"],
                            "action_input": parsed_action_input,
                            "reward": st.session_state.reward,
                            "info": info,
                            "reason": reason,
                        }
                    )
                    st.session_state.logs.append(
                        f"{info.get('ticket_status', '')} | {action_payload['action_type']} | reward={st.session_state.reward.get('reward_score', 0.0):.2f} | {reason}"
                    )
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON in action input: {e}")
                except ValueError as e:
                    st.error(str(e))
                except requests.RequestException as e:
                    st.error(f"Step failed: {e}")

    st.divider()
    st.subheader("Steps Taken")
    if st.session_state.actions_history:
        for idx, item in enumerate(st.session_state.actions_history, start=1):
            st.caption(f"{idx}. {item['action_type']} | reward={item['reward'].get('reward_score', 0.0):.2f}")

    st.divider()
    st.subheader("Logs")
    if st.session_state.logs:
        for line in st.session_state.logs[-12:]:
            st.write(line)
    else:
        st.caption("No logs yet.")

    st.divider()
    st.subheader("Environment State Viewer")
    if st.session_state.episode_id:
        try:
            with st.spinner("Fetching /state..."):
                st_data = call_backend("GET", "/state", params={"episode_id": st.session_state.episode_id}).get("state")
            st.json(st_data)
        except requests.RequestException as e:
            st.error(f"Failed to fetch state: {e}")
    else:
        st.caption("Reset to populate state.")

