from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
from streamlit.errors import StreamlitSecretNotFoundError

from support_env.workflow_policy import workflow_for_task


def _get_backend_base_url() -> str:
    env_url = os.getenv("BACKEND_BASE_URL")
    if env_url:
        return env_url

    try:
        secret_url = st.secrets.get("BACKEND_BASE_URL", None)
        if secret_url:
            return str(secret_url)
    except StreamlitSecretNotFoundError:
        pass
    except Exception:
        pass

    return "http://localhost:8000"


BACKEND_BASE_URL = _get_backend_base_url()

st.set_page_config(page_title="AI Customer Support Command Center", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    /* Smooth view transitions (where supported) */
    ::view-transition-group(*),
    ::view-transition-old(*),
    ::view-transition-new(*) {
      animation-duration: 0.25s;
      animation-timing-function: cubic-bezier(0.19, 1, 0.22, 1);
    }
    /* ====== AI Customer Support Command Center Theme (professional) ====== */
    :root{
      --bg0:#0B0F14;             /* graphite */
      --bg1:#070A0D;             /* deeper graphite */
      --card:rgba(255,255,255,.055);
      --card2:rgba(255,255,255,.075);
      --stroke:rgba(255,255,255,.09);
      --stroke2:rgba(255,255,255,.14);
      --text:#E7E9EE;
      --muted:rgba(231,233,238,.72);
      --muted2:rgba(231,233,238,.55);
      --shadow: 0 18px 48px rgba(0,0,0,.46);
      --shadow2: 0 10px 28px rgba(0,0,0,.38);
      --r12: 12px;
      --r16: 16px;

      /* Graphite + emerald + violet accents (no blue/orange) */
      --neonBlue:#2BD4A7;        /* mint/emerald accent */
      --purple:#B58CFF;          /* violet accent */
      --emerald:#10B981;
      --green:#22C55E;
      --amber:#A3E635;           /* lime */
      --red:#EF4444;
      --neutral:#9CA3AF;
    }

    /* App background */
    .stApp{
      background:
        radial-gradient(1100px circle at 12% -12%, rgba(43,212,167,.16), transparent 58%),
        radial-gradient(1100px circle at 78% 6%, rgba(181,140,255,.13), transparent 60%),
        radial-gradient(1000px circle at 86% 78%, rgba(163,230,53,.08), transparent 58%),
        radial-gradient(900px circle at 74% 72%, rgba(239,68,68,.05), transparent 55%),
        linear-gradient(180deg, var(--bg0), var(--bg1));
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif;
    }

    /* Spacing (leave room for sticky topbar) */
    .block-container{ padding-top: 5.75rem; padding-bottom: 1.35rem; }

    /* Typography tweaks */
    h1,h2,h3{ letter-spacing: -0.02em; }
    div[data-testid="stMetricValue"]{ font-weight: 850; letter-spacing: -0.02em; }
    div[data-testid="stMetricLabel"]{ color: var(--muted2); }

    /* Hide sidebar (top navbar design) */
    section[data-testid="stSidebar"]{ display:none; }

    /* Hide Streamlit chrome */
    header[data-testid="stHeader"]{ display:none; }
    footer{ display:none; }

    /* Buttons */
    .stButton > button{
      border-radius: 14px !important;
      border: 1px solid rgba(255,255,255,.10) !important;
      background: rgba(255,255,255,.06) !important;
      color: var(--text) !important;
      transition: transform .12s ease, background .12s ease, border-color .12s ease, box-shadow .12s ease;
      box-shadow: 0 6px 18px rgba(0,0,0,.22);
    }
    .stButton > button:hover{
      transform: translateY(-1px);
      background: rgba(255,255,255,.085) !important;
      border-color: rgba(255,255,255,.16) !important;
      box-shadow: 0 12px 28px rgba(0,0,0,.35);
    }
    .stButton > button:active{ transform: translateY(0px) scale(.99); }

    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"]{
      background: rgba(255,255,255,.05) !important;
      border: 1px solid rgba(255,255,255,.10) !important;
      border-radius: 14px !important;
      color: var(--text) !important;
    }

    /* Expanders */
    details{
      border-radius: var(--r16) !important;
      border: 1px solid rgba(255,255,255,.08) !important;
      background: rgba(255,255,255,.04) !important;
      box-shadow: 0 10px 30px rgba(0,0,0,.25);
    }
    details summary{ padding: 10px 14px !important; }

    /* Generic “glass card” helper */
    .cc-card{
      border-radius: 18px;
      border: 1px solid var(--stroke);
      background: linear-gradient(180deg, rgba(255,255,255,.070), rgba(255,255,255,.040));
      box-shadow: var(--shadow2);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
    }
    .cc-card:hover{
      border-color: rgba(255,255,255,.14);
      background: linear-gradient(180deg, rgba(255,255,255,.082), rgba(255,255,255,.045));
    }

    /* KPI mini cards */
    .cc-kpi{
      padding: 14px 14px;
      transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease;
    }
    .cc-kpi:hover{ transform: translateY(-2px); box-shadow: var(--shadow); }
    .cc-kpi-label{ color: var(--muted2); font-size: 12px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
    .cc-kpi-value{ font-size: 22px; font-weight: 900; letter-spacing: -0.02em; margin-top: 6px; }
    .cc-kpi-sub{ color: var(--muted); font-size: 12px; margin-top: 6px; }

    /* Pills */
    .cc-pill{
      display:inline-flex; align-items:center; gap:8px;
      padding:6px 10px; border-radius:999px;
      border: 1px solid rgba(255,255,255,.10);
      background: rgba(255,255,255,.05);
      font-weight: 800; font-size: 12px; color: var(--text);
    }
    .cc-dot{ width:8px; height:8px; border-radius:99px; display:inline-block; }
    .cc-dot-ok{ background: var(--green); box-shadow: 0 0 0 4px rgba(34,197,94,.12); }
    .cc-dot-warn{ background: var(--amber); box-shadow: 0 0 0 4px rgba(245,158,11,.12); }
    .cc-dot-bad{ background: var(--red); box-shadow: 0 0 0 4px rgba(239,68,68,.12); }
    .cc-dot-blue{ background: var(--neonBlue); box-shadow: 0 0 0 4px rgba(43,212,167,.16); }
    .cc-dot-purple{ background: var(--purple); box-shadow: 0 0 0 4px rgba(181,140,255,.16); }

    /* Top navbar */
    .cc-navbar{
      border-radius: 20px;
      border: 1px solid rgba(255,255,255,.10);
      background: linear-gradient(180deg, rgba(255,255,255,.085), rgba(255,255,255,.045));
      box-shadow: var(--shadow2);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      padding: 10px 12px;
    }

    .cc-topbar-wrap{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 999;
      padding: 14px 18px 0 18px;
      pointer-events: none; /* allow underlying Streamlit to remain scrollable */
    }
    .cc-topbar{
      pointer-events: auto; /* re-enable interactions inside */
      max-width: 1400px;
      margin: 0 auto;
    }
    .cc-brand{
      display:flex;
      flex-direction:column;
      gap:2px;
      padding: 10px 12px;
    }
    .cc-brand-title{ font-weight: 950; letter-spacing:-0.02em; line-height:1.1; }
    .cc-brand-sub{ color:rgba(231,233,238,.55); font-size:12px; line-height:1.1; }
    .cc-nav{
      display:flex;
      align-items:center;
      gap:8px;
      flex-wrap: wrap;
      padding: 8px 10px;
    }
    .cc-nav a{
      text-decoration:none;
      color: rgba(231,233,238,.78);
      font-weight: 850;
      font-size: 13px;
      padding: 8px 12px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,.08);
      background: rgba(255,255,255,.03);
      transition: transform .12s ease, background .12s ease, border-color .12s ease;
    }
    .cc-nav a:hover{
      transform: translateY(-1px);
      color: rgba(231,233,238,.92);
      background: rgba(255,255,255,.07);
      border-color: rgba(255,255,255,.14);
    }
    .cc-nav a.cc-active{
      color: rgba(231,233,238,1);
      background: linear-gradient(180deg, rgba(79,157,255,.22), rgba(255,255,255,.05));
      border-color: rgba(79,157,255,.35);
      box-shadow: 0 10px 28px rgba(0,0,0,.30);
    }
    .cc-nav-spacer{ flex: 1 1 auto; }
    .cc-nav .cc-cta{
      color: rgba(231,233,238,1);
      background: linear-gradient(180deg, rgba(124,92,255,.25), rgba(255,255,255,.05));
      border-color: rgba(124,92,255,.38);
    }

    /* Reduce extra whitespace above first element (since header is fixed) */
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"]) { scroll-margin-top: 90px; }

    /* Live pulse */
    .cc-live{ animation: cc-pulse 1.4s ease-in-out infinite; }
    @keyframes cc-pulse{
      0%, 100%{ box-shadow: 0 0 0 0 rgba(79,157,255,.22); }
      50%{ box-shadow: 0 0 0 8px rgba(79,157,255,.06); }
    }

    /* Shimmer for AI thinking */
    .cc-shimmer{ position: relative; overflow: hidden; }
    .cc-shimmer:after{
      content:"";
      position:absolute;
      inset:0;
      transform: translateX(-120%);
      background: linear-gradient(90deg, transparent, rgba(255,255,255,.10), transparent);
      animation: cc-shimmer 1.05s infinite;
    }
    @keyframes cc-shimmer{
      0%{ transform: translateX(-120%); }
      100%{ transform: translateX(120%); }
    }

    /* “thinking” dots animation */
    .cc-thinking{ display:inline-flex; align-items:center; gap:8px; }
    .cc-dots{ display:inline-flex; gap:5px; align-items:center; }
    .cc-dots span{
      width:6px; height:6px; border-radius:999px;
      background: rgba(231,233,238,.70);
      animation: cc-bounce 1.05s infinite ease-in-out;
    }
    .cc-dots span:nth-child(2){ animation-delay: .12s; }
    .cc-dots span:nth-child(3){ animation-delay: .24s; }
    @keyframes cc-bounce{
      0%, 80%, 100%{ transform: translateY(0); opacity:.55; }
      40%{ transform: translateY(-4px); opacity:1; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


STATUS_COLORS = {
    "OPEN": "#9CA3AF",  # neutral grey
    "IN_PROGRESS": "#F59E0B",  # amber
    "WAITING_FOR_CUSTOMER": "#F59E0B",  # amber
    "WAITING_FOR_CONFIRMATION": "#F59E0B",  # amber
    "RESOLVED": "#10B981",  # emerald
    "CLOSED": "#6B7280",  # neutral grey (darker)
    "REOPENED": "#EF4444",  # red (attention)
    "ESCALATED": "#EF4444",  # red
}

ACTION_TYPES = [
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


TASK_LABELS = {
    "easy_password_reset": "Easy - Password Reset",
    "medium_billing_missing_info": "Medium - Billing Issue",
    "hard_technical_troubleshooting": "Hard - Technical Issue",
}


@dataclass(frozen=True)
class TaskMeta:
    task_id: str
    label: str
    difficulty: str
    sla_seconds: float
    max_steps: int
    optimal_steps: int
    expected_issue_type: str


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#95A5A6")
    return f"""
<span style="
  display:inline-block;
  padding:4px 10px;
  border-radius:999px;
  background:{color};
  color:white;
  font-weight:700;
  font-size:12px;">
{status}
</span>
"""


def _backend_unreachable_message(exc: BaseException) -> str:
    return (
        f"{exc}\n\n"
        "The API server is not reachable. Start it in a separate terminal from the project root:\n\n"
        "  uvicorn server.app:app --host 127.0.0.1 --port 8000\n\n"
        f"If it runs elsewhere, set `BACKEND_BASE_URL` (current: `{BACKEND_BASE_URL}`)."
    )


def call_backend(method: str, path: str, json_payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    url = f"{BACKEND_BASE_URL}{path}"
    try:
        r = requests.request(method=method, url=url, json=json_payload, params=params, timeout=25)
        r.raise_for_status()
        return r.json()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise requests.exceptions.ConnectionError(_backend_unreachable_message(e)) from e


def safe_json_loads(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Action input JSON must be an object/dictionary.")
    return parsed


def get_tasks_meta() -> Dict[str, TaskMeta]:
    raw = call_backend("GET", "/tasks").get("tasks", [])
    metas: Dict[str, TaskMeta] = {}
    for t in raw:
        task_id = t.get("task_id")
        if not task_id:
            continue
        metas[task_id] = TaskMeta(
            task_id=task_id,
            label=t.get("label") or TASK_LABELS.get(task_id, task_id),
            difficulty=t.get("difficulty", "unknown"),
            sla_seconds=float(t.get("sla_seconds", 0.0) or 0.0),
            max_steps=int(t.get("max_steps", 0) or 0),
            optimal_steps=int(t.get("optimal_steps", t.get("max_steps", 0) or 0) or 0),
            expected_issue_type=t.get("expected_issue_type", ""),
        )
    return metas


def ensure_state() -> None:
    defaults = {
        "episode_id": None,
        "task_id": "easy_password_reset",
        "observation": None,
        "done": False,
        "reward": None,
        "steps_taken": 0,
        "actions_history": [],  # list of {action_type, action_input, reward, info}
        "logs": [],
        "mode": "Manual",  # Manual / AI Auto
        "thinking_steps": [],  # current thought steps
        "thought_history": [],  # per action
        "episode_history": [],  # per episode summary
        "tasks_meta": {},
        "selected_action_type": "classify_ticket",
        # UI-wide “tickets DB” so pages can show multiple tickets even when backend provides only one active episode.
        # This makes Tickets/Dashboard feel connected and non-empty.
        "tickets_db": [],  # list[dict]
        "selected_ticket_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if not st.session_state.tasks_meta:
        try:
            st.session_state.tasks_meta = get_tasks_meta()
        except Exception:
            st.session_state.tasks_meta = {}


def typing_effect(text: str, placeholder, speed_s: float = 0.008, max_chars: int = 240) -> None:
    text = text[:max_chars]
    out = ""
    for ch in text:
        out += ch
        placeholder.markdown(out)
        time.sleep(speed_s)


def show_ai_thinking(thought_steps: List[str], decision_header: str) -> None:
    st.subheader("AI Thinking Visualizer")
    st.caption("Static trace (per action). Expand each block for plain-text rationale.")
    st.write(decision_header)

    for i, step in enumerate(thought_steps, start=1):
        with st.expander(f"Trace {i} — {step.splitlines()[0][:72]}", expanded=(i == 1)):
            st.text(step)


def infer_current_stage(
    task_id: str, actions: List[dict], observation: Optional[dict] = None
) -> Tuple[str, int, Dict[str, bool]]:
    """
    State-aware stage label (ticket status + workflow), not only “have we ever taken action X”.
    """
    has = lambda t: any(a.get("action_type") == t for a in actions)
    classify = has("classify_ticket")
    search = has("search_knowledge_base")
    ask = has("ask_customer_question")
    send = has("send_response")
    confirm = has("confirm_customer_resolution")
    resolve = has("resolve_ticket")
    close = has("close_ticket")
    ask_count = sum(1 for a in actions if a.get("action_type") == "ask_customer_question")
    status = (observation or {}).get("ticket_status") or ""

    done_map = {
        "classify_ticket": classify,
        "search_knowledge_base": search,
        "ask_customer_question": ask,
        "send_response": send,
        "confirm_customer_resolution": confirm,
        "resolve_ticket": resolve,
        "close_ticket": close,
    }

    if status == "WAITING_FOR_CUSTOMER":
        return "Waiting for Customer Reply", 3, done_map
    if status == "WAITING_FOR_CONFIRMATION":
        return "Awaiting Customer Confirmation", 3, done_map
    if status == "REOPENED":
        return "Reopened — Send Updated Response", 3, done_map
    if status == "RESOLVED":
        return "Resolved — Close or Reopen", 4, done_map
    if status in ("CLOSED", "ESCALATED"):
        return "Episode Complete", 5, done_map

    if not classify:
        return "Start", 0, done_map

    requires_ask = task_id != "easy_password_reset"
    min_asks = 2 if task_id == "hard_technical_troubleshooting" else 1
    if requires_ask and ask_count < min_asks:
        return "Ask Customer", 3, done_map

    if not search:
        return "Search KB", 2, done_map

    if not send:
        return "Send Response", 3, done_map

    if not confirm:
        return "Awaiting Customer Confirmation", 3, done_map

    if not resolve:
        return "Resolve Ticket", 4, done_map

    if not close:
        return "Close Ticket", 5, done_map

    return "Episode Complete", 5, done_map


def render_decision_flow_graph(task_id: str, actions: List[dict], observation: Optional[dict] = None) -> None:
    stage_name, stage_idx, done_map = infer_current_stage(task_id, actions, observation)
    st.subheader("Decision Flow Graph")

    # Node positions (fixed coordinates for a consistent “mission control” layout)
    nodes = [
        ("Start", 0.0, 0.8),
        ("Classify Ticket", 0.2, 0.6),
        ("Search KB", 0.4, 0.4),
        ("Ask Customer", 0.6, 0.2),
        ("Resolve Ticket", 0.8, 0.4),
        ("Close Ticket", 1.0, 0.6),
    ]
    # Map node index to our stage indices
    active_node_idx = stage_idx

    # Edge list
    edges = [
        ((0.0, 0.8), (0.2, 0.6)),
        ((0.2, 0.6), (0.4, 0.4)),
        ((0.4, 0.4), (0.6, 0.2)),
        ((0.6, 0.2), (0.8, 0.4)),
        ((0.8, 0.4), (1.0, 0.6)),
    ]

    fig = go.Figure()
    for (x0, y0), (x1, y1) in edges:
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color="#64748B", width=3),
                opacity=0.65,
                hoverinfo="skip",
                showlegend=False,
            )
        )

    node_colors = ["#94A3B8"] * len(nodes)
    node_colors[active_node_idx] = "#F59E0B"  # highlight current (amber)

    # Mark completed nodes using done_map heuristics.
    # If classification/search/etc happened, color the corresponding nodes as “done”.
    if done_map["classify_ticket"]:
        node_colors[1] = "#10B981"
    if done_map["search_knowledge_base"]:
        node_colors[2] = "#10B981"
    if task_id != "easy_password_reset" and done_map["ask_customer_question"]:
        node_colors[3] = "#10B981"
    if done_map.get("send_response"):
        node_colors[3] = "#10B981"
    if done_map.get("confirm_customer_resolution"):
        node_colors[3] = "#10B981"
    if done_map["resolve_ticket"]:
        node_colors[4] = "#10B981"
    if done_map["close_ticket"]:
        node_colors[5] = "#10B981"

    fig.add_trace(
        go.Scatter(
            x=[n[1] for n in nodes],
            y=[n[2] for n in nodes],
            mode="markers+text",
            text=[n[0] for n in nodes],
            textposition="bottom center",
            marker=dict(size=38, color=node_colors, line=dict(width=2, color="#0F172A")),
            hovertemplate="%{text}<extra></extra>",
        )
    )

    fig.update_layout(
        height=310,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Current mission phase: **{stage_name}**")


def render_timeline(task_id: str, actions: List[dict], max_steps: int) -> None:
    """
    Dynamic timeline: records every action the user/agent took in order.
    This fixes “timeline not recording all steps” for hard tasks with duplicate questions/searches.
    """
    st.subheader("Live Episode Timeline (Animated)")

    if not actions:
        st.info("Timeline will populate after you take the first action (Reset first).")
        return

    # Live time summary (if available)
    try:
        obs = st.session_state.get("observation") or {}
        t_elapsed = float(obs.get("time_elapsed", 0.0) or 0.0)
        tm = st.session_state.tasks_meta.get(st.session_state.task_id)
        sla = float((tm.sla_seconds if tm else 0.0) or 0.0)
        if sla:
            st.caption(f"Time elapsed: **{t_elapsed:.0f}s** / SLA **{sla:.0f}s**")
        else:
            st.caption(f"Time elapsed: **{t_elapsed:.0f}s**")
    except Exception:
        pass

    # NOTE: We intentionally do not show a big progress bar here.
    # Users often confuse it with ticket lifecycle; the detailed cards below are the real “timeline”.

    prev_t: Optional[float] = None
    for i, item in enumerate(actions, start=1):
        a_type = item.get("action_type", "—")
        reward = item.get("reward") or {}
        reward_score = float(reward.get("reward_score", 0.0) or 0.0)
        action_input = item.get("action_input") or {}
        status = item.get("info", {}).get("ticket_status", "")
        t_step = item.get("info", {}).get("time_elapsed", None)
        try:
            t_step_f = float(t_step) if t_step is not None and t_step != "" else None
        except Exception:
            t_step_f = None
        dt = (t_step_f - prev_t) if (t_step_f is not None and prev_t is not None) else None
        if t_step_f is not None:
            prev_t = t_step_f
        color = STATUS_COLORS.get(status, "#94A3B8") if status else "#94A3B8"

        time_line = ""
        if t_step_f is not None:
            if dt is not None and dt >= 0:
                time_line = f"<div style='color:rgba(255,255,255,0.70); font-size:12px; margin-top:4px;'>time: {t_step_f:.0f}s <span style='opacity:.75'>(+{dt:.0f}s)</span></div>"
            else:
                time_line = f"<div style='color:rgba(255,255,255,0.70); font-size:12px; margin-top:4px;'>time: {t_step_f:.0f}s</div>"

        st.markdown(
            f"""
            <div title="action_input={json.dumps(action_input)[:240]}" style="
              border:2px solid rgba(15,23,42,0.20);
              border-radius:16px;
              padding:12px;
              background:rgba(255,255,255,0.06);
              margin-bottom:10px;
            ">
              <div style="display:flex; gap:12px; align-items:center; justify-content:space-between;">
                <div>
                  <div style="font-weight:950; font-size:14px; color:{color};">Step {i}</div>
                  <div style="color:white; font-weight:800; font-size:13px; margin-top:4px;">{a_type}</div>
                  {time_line}
                </div>
                <div style="text-align:right;">
                  <div style="font-weight:900; font-size:14px;">reward: {reward_score:+.2f}</div>
                  <div style="color:rgba(255,255,255,0.75); font-size:12px; margin-top:4px;">ticket: {status or '—'}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Show action input (transparency)"):
            st.json(action_input)


def compute_reward_intelligence(
    task_meta: Optional[TaskMeta],
    observation: Optional[dict],
    actions: List[dict],
    *,
    steps_taken: Optional[int] = None,
) -> dict:
    """
    Computes an explainable “reward intelligence” breakdown using environment + action history heuristics.

    Efficiency (heuristic panel): 100% while step count is at or below optimal_steps; if you exceed optimal
    before max_steps, it falls off linearly to 0% at max_steps (aligned with task budgets in openenv/tasks).
    """
    if task_meta is None:
        return {
            "components": {},
            "total_estimate": 0.0,
            "efficiency_score": 0.0,
            "step_efficiency_score": 0.0,
            "time_efficiency_score": 0.0,
            "delay_penalty": 0.0,
            "trend_rewards": [],
            "sum_step_rewards": 0.0,
            "steps_for_efficiency": 0,
            "optimal_steps": 0,
            "max_steps": 0,
            "top_kb_relevance": 0.0,
            "wrong_classification": False,
            "raw_total": 0.0,
        }

    expected_issue = task_meta.expected_issue_type
    sla = float(task_meta.sla_seconds or 0.0)
    max_steps = int(task_meta.max_steps or 0)
    optimal_steps = int(task_meta.optimal_steps or 0)

    # classification
    classify_actions = [a for a in actions if a.get("action_type") == "classify_ticket"]
    classified_ok = False
    if classify_actions:
        last_input = classify_actions[-1].get("action_input") or {}
        provided_issue = last_input.get("issue_type") or last_input.get("predicted_issue_type") or ""
        classified_ok = provided_issue == expected_issue

    # KB usage + relevance from environment (observation), not UI guesses
    search_actions = [a for a in actions if a.get("action_type") == "search_knowledge_base"]
    kb_results = (observation or {}).get("knowledge_base_results", []) or []
    kb_used_ok = len(search_actions) >= 1 and any(r.get("matched") for r in kb_results if isinstance(r, dict))
    rel_scores = [float(r.get("relevance_score") or 0.0) for r in kb_results if isinstance(r, dict)]
    top_kb_relevance = max(rel_scores) if rel_scores else 0.0

    # response helpfulness / correctness
    send_actions = [a for a in actions if a.get("action_type") == "send_response"]
    response_text = ""
    if send_actions:
        last_input = send_actions[-1].get("action_input") or {}
        response_text = last_input.get("response") or last_input.get("message") or last_input.get("text") or ""
    response_text_l = (response_text or "").lower()

    # Required keywords by task (same spirit as environment/grader)
    if task_meta.task_id == "easy_password_reset":
        must = ["forgot password", "reset link", "new password"]
    elif task_meta.task_id == "medium_billing_missing_info":
        must = ["refund", "duplicate", "invoice"]
    else:
        must = ["forget the network", "power-cycle", "router firmware", "dns", "switch band"]

    response_ok = False
    hit = 0
    for kw in must:
        if kw.lower() in response_text_l:
            hit += 1
    response_ok = hit >= max(1, len(must) // 2)

    confirm_actions = [a for a in actions if a.get("action_type") == "confirm_customer_resolution"]
    confirmation_ok = bool(confirm_actions) and any(
        float((x.get("reward") or {}).get("reward_score", 0.0) or 0.0) > 0.05 for x in confirm_actions
    )

    # SLA: gradual pressure (not only binary)
    time_elapsed = float((observation or {}).get("time_elapsed", 0.0) or 0.0)
    delay_penalty = 1.0 if sla and time_elapsed > sla else 0.0
    if sla and sla > 0:
        if time_elapsed <= sla:
            time_efficiency = 1.0
        else:
            time_efficiency = max(0.0, 1.0 - (time_elapsed - sla) / sla)
        sla_ratio = time_elapsed / sla
    else:
        time_efficiency = 1.0
        sla_ratio = 0.0

    steps_count = int(steps_taken) if steps_taken is not None else len(actions)
    step_efficiency_score = 0.0
    if optimal_steps > 0 and max_steps > 0 and steps_count > 0:
        if steps_count <= optimal_steps:
            step_efficiency_score = 1.0
        else:
            over = steps_count - optimal_steps
            span = max(1, max_steps - optimal_steps)
            step_efficiency_score = max(0.0, 1.0 - (over / float(span)))
    elif max_steps > 0 and steps_count > 0 and optimal_steps <= 0:
        step_efficiency_score = max(0.0, 1.0 - (steps_count / float(max_steps)))

    # Combined efficiency: steps + clock (issue #1, #16)
    if sla:
        efficiency_score = 0.55 * step_efficiency_score + 0.45 * time_efficiency
    else:
        efficiency_score = step_efficiency_score

    wrong_class = bool(classify_actions) and not classified_ok
    class_pts = 0.18 if classified_ok else (-0.14 if wrong_class else 0.0)
    kb_pts = 0.14 if kb_used_ok else 0.0
    if kb_used_ok and top_kb_relevance > 0:
        kb_pts += 0.06 * min(1.0, top_kb_relevance / 0.92)

    over_opt = max(0, steps_count - optimal_steps)
    span_steps = max(1, max_steps - optimal_steps) if max_steps > optimal_steps else 1
    step_budget_penalty = -0.07 * min(1.0, over_opt / float(span_steps)) if optimal_steps and max_steps else 0.0

    components = {
        "classification": class_pts,
        "kb_usage": kb_pts,
        "correct_response": 0.26 if response_ok else 0.0,
        "customer_confirmation": 0.12 if confirmation_ok else 0.0,
        "efficiency": 0.12 * efficiency_score,
        "step_budget_penalty": step_budget_penalty,
        "sla_pressure": (-0.1 * delay_penalty - 0.04 * max(0.0, sla_ratio - 0.85)) if sla else 0.0,
    }

    raw_total = float(sum(components.values()))
    total_estimate = float(max(0.0, min(1.0, raw_total)))

    trend_rewards = []
    sum_step_rewards = 0.0
    for a in actions:
        r = a.get("reward") or {}
        if isinstance(r, dict) and "reward_score" in r and r["reward_score"] is not None:
            trend_rewards.append(float(r["reward_score"]))
            sum_step_rewards += float(r["reward_score"])

    return {
        "components": components,
        "total_estimate": total_estimate,
        "efficiency_score": float(efficiency_score),
        "step_efficiency_score": float(step_efficiency_score),
        "time_efficiency_score": float(time_efficiency) if sla else float(step_efficiency_score),
        "delay_penalty": float(delay_penalty),
        "trend_rewards": trend_rewards,
        "sum_step_rewards": float(sum_step_rewards),
        "steps_for_efficiency": steps_count,
        "optimal_steps": optimal_steps,
        "max_steps": max_steps,
        "top_kb_relevance": float(top_kb_relevance),
        "wrong_classification": wrong_class,
        "raw_total": raw_total,
    }


def render_reward_intelligence_panel(task_meta: Optional[TaskMeta], observation: Optional[dict], actions: List[dict]) -> None:
    st.subheader("Reward Intelligence Panel")
    steps_hint = getattr(st.session_state, "steps_taken", None)
    rinfo = compute_reward_intelligence(task_meta, observation, actions, steps_taken=steps_hint)
    total = rinfo["total_estimate"]
    sum_steps = rinfo.get("sum_step_rewards", 0.0)
    se = rinfo.get("steps_for_efficiency", len(actions))
    opt = rinfo.get("optimal_steps", 0)
    mx = rinfo.get("max_steps", 0)

    st.info(
        "Two different signals: (1) **Environment** — each step returns `reward_score` (summed below). "
        "(2) **Dashboard heuristic** — the composite score and pie chart estimate quality from your action history; "
        "it is not the same number as (1)."
    )
    st.caption(f"Sum of environment step rewards (Σ `reward_score`): **{sum_steps:.2f}**")

    # Total progress bar
    eff_pct = rinfo["efficiency_score"] * 100.0
    ste = rinfo.get("step_efficiency_score", rinfo["efficiency_score"]) * 100.0
    te = rinfo.get("time_efficiency_score", 1.0) * 100.0
    eff_note = (
        f"Steps: {se} / max {mx} (target ≤ {opt}). "
        f"Combined efficiency blends step budget (~{ste:.0f}%) and SLA time (~{te:.0f}%)."
    )
    st.markdown(
        f"""
        <div style="background:rgba(255,255,255,0.06); padding:12px; border-radius:16px; border:1px solid rgba(255,255,255,0.08);">
          <div style="font-weight:900; font-size:16px;">Heuristic composite: {total:.2f}</div>
          <div style="color:rgba(255,255,255,0.75); margin-top:6px;">Budget efficiency (heuristic): {eff_pct:.0f}%</div>
          <div style="color:rgba(255,255,255,0.55); margin-top:4px; font-size:12px;">{eff_note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_reward_pie_compact(task_meta: Optional[TaskMeta], observation: Optional[dict], actions: List[dict]) -> None:
    """
    Compact reward pie for the Dashboard (same signals as Reward page).
    """
    steps_hint = getattr(st.session_state, "steps_taken", None)
    rinfo = compute_reward_intelligence(task_meta, observation, actions, steps_taken=steps_hint)
    total = float(rinfo.get("total_estimate", 0.0) or 0.0)
    comp = rinfo.get("components") or {}
    eff_pct = float(rinfo.get("efficiency_score", 0.0) or 0.0) * 100.0

    st.subheader("Reward Intelligence (Quick)")
    st.caption(f"Heuristic composite: **{total:.2f}**  •  Σ env rewards: **{float(rinfo.get('sum_step_rewards', 0.0) or 0.0):.2f}**")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Correct Classification", "No" if rinfo.get("wrong_classification") else "Yes")
        st.metric("KB Usage / relevance", f"{rinfo.get('top_kb_relevance', 0):.2f} peak" if float(comp.get("kb_usage", 0.0) or 0.0) > 0 else "No")
        st.metric("Customer Confirmed", "Yes" if comp.get("customer_confirmation", 0) > 0 else "No")
    with col_b:
        st.metric("SLA pressure", "High" if rinfo["delay_penalty"] > 0 else "OK")
        st.metric("Budget efficiency", f"{eff_pct:.0f}%")
        st.caption("Heuristic only; full details on Reward page.")

    pie_labels = []
    pie_values = []
    for k in ["classification", "kb_usage", "correct_response", "customer_confirmation", "efficiency"]:
        pie_labels.append(k)
        pie_values.append(max(0.0, float(comp.get(k, 0.0) or 0.0)))
    if sum(pie_values) <= 0:
        pie_values = [1] * max(1, len(pie_labels))
    pie_fig = px.pie(names=pie_labels, values=pie_values, title="")
    pie_fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
    _plotly_theme(pie_fig)
    st.plotly_chart(pie_fig, use_container_width=True)


def render_sla_visualizer(task_meta: Optional[TaskMeta], observation: Optional[dict]) -> None:
    if task_meta is None:
        return
    sla = float(task_meta.sla_seconds or 0.0)
    time_elapsed = float((observation or {}).get("time_elapsed", 0.0) or 0.0)
    remaining = max(0.0, sla - time_elapsed)
    percent = 1.0 if sla <= 0 else remaining / sla

    if percent > 0.5:
        cls = "sla-ok"
    elif percent > 0.2:
        cls = "sla-warn"
    else:
        cls = "sla-danger"

    st.subheader("SLA Pressure Visualizer")
    st.markdown(
        f"""
        <style>
        .sla-timer {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size:22px; font-weight:900; padding:10px 14px; border-radius:16px; border:1px solid rgba(255,255,255,0.10); display:inline-block; }}
        .sla-ok {{ background: rgba(16,185,129,0.16); color: #10B981; }}
        .sla-warn {{ background: rgba(245,158,11,0.16); color: #F59E0B; }}
        .sla-danger {{ background: rgba(239,68,68,0.18); color: #EF4444; animation: flash 0.8s infinite; }}
        @keyframes flash {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.55; }}
            100% {{ opacity: 1; }}
        }}
        </style>
        <div>
          <div class="sla-timer {cls}" id="sla_timer">calculating...</div>
          <div style="margin-top:8px; color: rgba(255,255,255,0.75);">SLA Countdown + color pressure</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Client-side countdown animation (does not require Streamlit reruns)
    remaining_int = int(remaining)
    warn_threshold = int(sla * 0.2) if sla else 0
    danger_threshold = int(sla * 0.1) if sla else 0
    st.markdown(
        f"""
        <script>
        (function(){{
          const el = document.getElementById("sla_timer");
          if(!el) return;
          let t = {remaining_int};
          const pad = (n) => n.toString().padStart(2,'0');
          function tick(){{
            if(t < 0) t = 0;
            const m = Math.floor(t/60);
            const s = t % 60;
            el.innerText = pad(m)+":"+pad(s)+" remaining";
            if({warn_threshold} > 0 && t <= {danger_threshold}) el.className = "sla-timer sla-danger";
            else if({warn_threshold} > 0 && t <= {warn_threshold}) el.className = "sla-timer sla-warn";
            else el.className = "sla-timer sla-ok";
            t -= 1;
          }}
          tick();
          setInterval(tick, 1000);
        }})();
        </script>
        """,
        unsafe_allow_html=True,
    )


def explain_ticket_status(ticket_status: str) -> str:
    mapping = {
        "OPEN": "The ticket is newly created. The agent must classify the issue before taking corrective actions.",
        "IN_PROGRESS": "The agent is working on the ticket using the knowledge base and customer communication.",
        "WAITING_FOR_CUSTOMER": "The agent is waiting for customer-provided missing information (e.g., invoice number or diagnostics).",
        "WAITING_FOR_CONFIRMATION": "The agent sent a customer-facing response; record customer acknowledgment with `confirm_customer_resolution` before resolving.",
        "RESOLVED": "A resolution has been drafted and accepted by internal checks. The agent should close the ticket next.",
        "CLOSED": "The ticket is closed. Episode is complete.",
        "ESCALATED": "Escalated to a specialist. Episode ends with human handoff (failure / handoff path).",
        "REOPENED": "Customer asked to continue after a resolution draft; send an updated response, then confirm and resolve again before closing.",
    }
    return mapping.get(ticket_status, "Unknown ticket state.")


def render_environment_state_explainer(task_meta: Optional[TaskMeta], observation: Optional[dict]) -> None:
    st.subheader("Environment State Explainer")
    if not observation:
        st.info("Reset the environment to see state explanations.")
        return
    ticket_status = observation.get("ticket_status", "—")
    priority = observation.get("ticket_priority", "—")
    st.markdown(status_badge(ticket_status), unsafe_allow_html=True)
    eid = observation.get("episode_id", "")
    st.markdown(
        f"""
        <div style="margin-top:10px; padding:12px; border-radius:16px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.08);">
          <div style="font-weight:900; margin-bottom:6px;">What this status means</div>
          <div style="color:rgba(255,255,255,0.82);">{explain_ticket_status(ticket_status)}</div>
          <div style="margin-top:8px; color:rgba(255,255,255,0.75);"><b>Episode ID:</b> {eid or "—"}</div>
          <div style="margin-top:8px; color:rgba(255,255,255,0.75);"><b>Priority:</b> {priority}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if task_meta and "time_elapsed" in observation and task_meta.sla_seconds:
        st.caption(f"Time elapsed: {observation.get('time_elapsed', 0.0):.0f}s / SLA {task_meta.sla_seconds:.0f}s")


def render_performance_analytics() -> None:
    st.subheader("Performance Analytics")
    history: List[dict] = st.session_state.episode_history
    if not history:
        st.info("Run at least one episode to populate performance analytics.")
        return

    # Summary stats from episode history
    avg_final_reward = sum(h["final_reward_score"] for h in history) / len(history)
    avg_steps = sum(h["steps_taken"] for h in history) / len(history)
    resolutions = [1 if h.get("success_closed") else 0 for h in history]
    success_rate = sum(resolutions) / len(resolutions)

    eff_scores: List[float] = []
    for h in history:
        opt = int(h.get("optimal_steps") or 0)
        mx = int(h.get("max_steps") or 0)
        stc = int(h.get("steps_taken") or 0)
        if opt > 0 and mx > opt:
            eff_scores.append(max(0.0, 1.0 - max(0, stc - opt) / float(mx - opt)))
        elif mx > 0:
            eff_scores.append(max(0.0, 1.0 - stc / float(mx)))
    avg_eff = sum(eff_scores) / len(eff_scores) if eff_scores else 0.0
    fail_rate = sum(1 for h in history if h.get("failure_episode")) / len(history)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Reward", f"{avg_final_reward:.2f}")
    with col2:
        st.metric("Step efficiency vs optimal", f"{avg_eff*100:.0f}%")
    with col3:
        st.metric("Clean close rate", f"{success_rate*100:.0f}%")
    with col4:
        st.metric("Failure / truncate rate", f"{fail_rate*100:.0f}%")

    # Trend chart (final rewards)
    y = [h["final_reward_score"] for h in history]
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=y, mode="lines+markers"))
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def action_expected_order(task_id: str) -> List[str]:
    try:
        return workflow_for_task(task_id)  # type: ignore[arg-type]
    except Exception:
        return ["classify_ticket", "search_knowledge_base", "send_response", "resolve_ticket", "close_ticket"]


def simulate_prediction(task_meta: Optional[TaskMeta], observation: Optional[dict], actions: List[dict], action_type: str, action_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    “Action Simulator” predicts outcome before sending action.
    """
    if task_meta is None:
        return {
            "predicted_reward_delta": 0.0,
            "success_probability": 0.0,
            "warnings": ["No task metadata loaded."],
            "recommended_next": None,
            "ai_thought_steps": ["Load tasks metadata by resetting the environment."],
        }

    order = action_expected_order(task_meta.task_id)
    used_idx: set[int] = set()
    stage_expected = None
    for expected in order:
        matched = False
        for j, a in enumerate(actions):
            if j in used_idx:
                continue
            if a.get("action_type") == expected:
                used_idx.add(j)
                matched = True
                break
        if not matched:
            stage_expected = expected
            break
    if stage_expected is None:
        stage_expected = "close_ticket"

    # Predict
    predicted_reward_delta = 0.0
    success_probability = 0.4
    warnings: List[str] = []

    if action_type == stage_expected:
        # Give a reward bump for in-order actions.
        if action_type == "classify_ticket":
            predicted_reward_delta = 0.20
            success_probability = 0.85
        elif action_type == "search_knowledge_base":
            predicted_reward_delta = 0.10
            success_probability = 0.80
        elif action_type == "ask_customer_question":
            predicted_reward_delta = 0.12
            success_probability = 0.75
        elif action_type == "send_response":
            predicted_reward_delta = 0.18
            success_probability = 0.78
        elif action_type == "confirm_customer_resolution":
            predicted_reward_delta = 0.08
            success_probability = 0.88
        elif action_type == "resolve_ticket":
            predicted_reward_delta = 0.25
            success_probability = 0.82
        elif action_type == "close_ticket":
            predicted_reward_delta = 0.15
            success_probability = 0.9
        elif action_type == "reopen_ticket":
            predicted_reward_delta = 0.06
            success_probability = 0.72
        else:
            predicted_reward_delta = 0.08
            success_probability = 0.6
    else:
        warnings.append("This action appears out-of-order. The environment may penalize or reject earlier workflow stages.")
        predicted_reward_delta = -0.05
        success_probability = 0.35

    # SLA-aware hint
    time_elapsed = float((observation or {}).get("time_elapsed", 0.0) or 0.0)
    sla = float(task_meta.sla_seconds or 0.0)
    if sla and time_elapsed > sla * 0.85 and action_type != "escalate_ticket":
        warnings.append("SLA is near expiration. Consider `escalate_ticket` if resolution cannot be completed in time.")

    # AI thinking steps for this specific action
    exp_issue = task_meta.expected_issue_type
    ai_steps = [
        f"Mission context: task is **{task_meta.task_id}** with expected issue type **{exp_issue}**.",
        f"Workflow check: expected next action is **{stage_expected}**.",
        f"Action simulator: `{'+' if predicted_reward_delta>=0 else ''}{predicted_reward_delta:.2f}` predicted reward delta and approx success probability **{success_probability*100:.0f}%**.",
        "Decision: send this action to reduce uncertainty (classification), retrieve evidence (KB), request missing info (questions), and draft a resolution (response).",
    ]
    if warnings:
        ai_steps.append(f"Risk flags: {', '.join(warnings)}")

    return {
        "predicted_reward_delta": predicted_reward_delta,
        "success_probability": success_probability,
        "warnings": warnings,
        "recommended_next": stage_expected,
        "ai_thought_steps": ai_steps,
    }


def render_action_simulator(task_meta: Optional[TaskMeta], observation: Optional[dict], actions: List[dict], action_type: str, action_input: Dict[str, Any]) -> None:
    st.subheader("Action Simulator (Predicted Outcome)")
    pred = simulate_prediction(task_meta, observation, actions, action_type, action_input)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Predicted Reward Delta", f"{pred['predicted_reward_delta']:+.2f}")
    with col2:
        st.metric("Success Probability", f"{pred['success_probability']*100:.0f}%")

    if pred["warnings"]:
        st.warning(" ; ".join(pred["warnings"]))
    else:
        st.success("Action looks aligned with the expected workflow.")

    st.caption(f"Recommended next (based on stage): `{pred['recommended_next']}`")

    with st.expander("Explain prediction (transparency)"):
        for s in pred["ai_thought_steps"]:
            st.markdown(f"- {s}")


def render_workflow_policy_panel(task_id: str, actions: List[dict]) -> None:
    st.subheader("Workflow Policy")
    policy = action_expected_order(task_id)
    taken = [a.get("action_type") for a in actions]
    used_idx: set[int] = set()
    for idx, expected in enumerate(policy):
        matched = False
        for j, got in enumerate(taken):
            if j in used_idx:
                continue
            if got == expected:
                used_idx.add(j)
                matched = True
                break
        marker = "✅" if matched else "⏳"
        st.markdown(f"{marker} `{expected}`")


def render_chat(conversation_history: List[str]) -> None:
    st.subheader("Live Chat Conversation")
    if not conversation_history:
        st.info("After reset, the first customer message appears here.")
        return

    for msg in conversation_history:
        if msg.startswith("Customer:"):
            bubble = msg.replace("Customer:", "").strip()
            with st.chat_message("user"):
                st.write(bubble)
        elif msg.startswith("Agent:"):
            bubble = msg.replace("Agent:", "").strip()
            with st.chat_message("assistant"):
                st.write(bubble)
        else:
            with st.chat_message("assistant"):
                st.write(msg)


def _plotly_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E7E9EE", family="Inter, ui-sans-serif, system-ui"),
        margin=dict(l=10, r=10, t=40, b=10),
        colorway=["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#9CA3AF"],
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)")
    return fig


def _kpi_card(label: str, value: str, sub: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="cc-card cc-kpi" style="border-color: rgba(255,255,255,.08);">
          <div class="cc-kpi-label">{label}</div>
          <div class="cc-kpi-value" style="color:{accent};">{value}</div>
          <div class="cc-kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(task_meta: Optional[TaskMeta], observation: Optional[dict], actions: List[dict]) -> None:
    obs = observation or {}
    rinfo = compute_reward_intelligence(task_meta, observation, actions, steps_taken=st.session_state.get("steps_taken"))
    eff = rinfo.get("efficiency_score", 0.0)
    steps_taken = int(st.session_state.get("steps_taken") or len(actions))
    max_steps = int((task_meta.max_steps if task_meta else 0) or 0)
    ticket_status = str(obs.get("ticket_status") or "—")

    # AI confidence proxy: top KB relevance + simulator success probability (if we can compute it)
    kb_rel = float(rinfo.get("top_kb_relevance", 0.0) or 0.0)
    conf = max(0.12, min(0.97, 0.55 * kb_rel + 0.42 * (0.75 if actions else 0.45)))

    c1, c2, c3, c4 = st.columns(4, gap="large")
    with c1:
        _kpi_card("Efficiency", f"{eff*100:.0f}%", "Step+SLA composite", "#10B981" if eff >= 0.72 else "#F59E0B")
    with c2:
        _kpi_card("Ticket status", ticket_status.replace("_", " "), "Live env state", STATUS_COLORS.get(ticket_status, "#9CA3AF"))
    with c3:
        _kpi_card("AI confidence", f"{conf*100:.0f}%", "Evidence-weighted", "#3B82F6" if conf >= 0.78 else "#F59E0B")
    with c4:
        _kpi_card("Steps", f"{steps_taken}/{max_steps or '—'}", "Budget utilization", "#F59E0B" if max_steps and steps_taken >= max_steps else "#9CA3AF")


def render_confidence_gauge(confidence: float) -> None:
    """
    Circular arc-style gauge for AI confidence.
    """
    c = max(0.0, min(1.0, float(confidence or 0.0)))
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=c * 100.0,
            number={"suffix": "%", "font": {"size": 30, "color": "#E7E9EE"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)"},
                "bar": {"color": "#3B82F6"},
                "bgcolor": "rgba(255,255,255,0.04)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "rgba(239,68,68,0.14)"},
                    {"range": [50, 78], "color": "rgba(245,158,11,0.14)"},
                    {"range": [78, 100], "color": "rgba(16,185,129,0.14)"},
                ],
                "threshold": {"line": {"color": "rgba(255,255,255,0.18)", "width": 2}, "thickness": 0.75, "value": 78},
            },
            title={"text": "AI Confidence", "font": {"size": 14, "color": "rgba(231,233,238,.72)", "family": "Inter"}},
        )
    )
    _plotly_theme(fig)
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=50, b=0))
    st.plotly_chart(fig, use_container_width=True)


def render_ticket_timeline(observation: Optional[dict], actions: List[dict]) -> None:
    """
    Vertical lifecycle timeline for the ticket.
    """
    status_now = str((observation or {}).get("ticket_status") or "OPEN")
    ticket_id = str((observation or {}).get("ticket_id") or "—")
    stages = ["OPEN", "IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_CONFIRMATION", "RESOLVED", "CLOSED"]
    if status_now == "ESCALATED":
        stages = ["OPEN", "IN_PROGRESS", "ESCALATED"]
    if status_now == "REOPENED":
        stages = ["OPEN", "IN_PROGRESS", "WAITING_FOR_CONFIRMATION", "RESOLVED", "REOPENED"]

    def stage_state(s: str) -> str:
        if s == status_now:
            return "active"
        if status_now in stages and s in stages and stages.index(s) < stages.index(status_now):
            return "done"
        # Heuristic: if an action implies stage completion, mark done
        at = [a.get("action_type") for a in actions]
        if s == "IN_PROGRESS" and "classify_ticket" in at:
            return "done"
        if s == "WAITING_FOR_CONFIRMATION" and "send_response" in at:
            return "done" if status_now in ("RESOLVED", "CLOSED") else "active"
        if s == "RESOLVED" and "resolve_ticket" in at:
            return "done" if status_now == "CLOSED" else "active"
        if s == "CLOSED" and "close_ticket" in at:
            return "done"
        return "todo"

    def dot_for(state: str) -> str:
        if state == "done":
            return "cc-dot-ok"
        if state == "active":
            return "cc-dot-blue"
        return "cc-dot-warn"

    rows = []
    for idx, s in enumerate(stages):
        stt = stage_state(s)
        is_last = idx == (len(stages) - 1)
        connector = (
            "<span style=\"width:2px; flex:1; background:rgba(255,255,255,.08); margin-top:6px; border-radius:2px;\"></span>"
            if not is_last
            else "<span style=\"width:2px; flex:1; background:rgba(0,0,0,0); margin-top:6px;\"></span>"
        )
        rows.append(
            f"""
            <div style="display:flex; gap:10px; align-items:flex-start; margin-top:10px;">
              <div style="display:flex; flex-direction:column; align-items:center; width:18px;">
                <span class="cc-dot {dot_for(stt)}" style="width:10px; height:10px; box-shadow:none;"></span>
                {connector}
              </div>
              <div style="padding-bottom:6px;">
                <div style="font-weight:950;">{s.replace('_',' ')}</div>
                <div style="color:rgba(231,233,238,.55); font-size:12px;">{('Current stage' if stt=='active' else ('Completed' if stt=='done' else 'Queued'))}</div>
              </div>
            </div>
            """
        )

    st.markdown(
        f"""
        <div class="cc-card" style="padding:14px 14px;">
          <div style="font-weight:950; letter-spacing:-0.02em; font-size:16px;">Ticket timeline</div>
          <div style="margin-top:6px; color:rgba(231,233,238,.55); font-size:12px;">
            <span style="font-weight:900;">{ticket_id}</span>
            <span style="margin:0 8px;">•</span>
            <span>Current: <span style="font-weight:900;">{status_now.replace('_',' ')}</span></span>
          </div>
          {''.join(rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_thinking_indicator(active: bool, label: str = "AI is thinking") -> None:
    if not active:
        return
    st.markdown(
        f"""
        <div class="cc-card" style="padding:10px 12px;">
          <div class="cc-thinking">
            <span style="color:rgba(231,233,238,.72); font-weight:800; font-size:12px; letter-spacing:.06em; text-transform:uppercase;">{label}</span>
            <span class="cc-dots" aria-label="thinking">
              <span></span><span></span><span></span>
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_modern(conversation_history: List[str], *, demo: bool = False) -> None:
    """
    Modern chat with avatars + timestamps.
    If no backend conversation is available, a small demo simulation is shown.
    """
    if "demo_chat" not in st.session_state:
        st.session_state.demo_chat = [
            {"role": "customer", "name": "Ava", "time": "09:14", "text": "Hi — I can’t log in. The reset email never arrives."},
            {"role": "assistant", "name": "Agent", "time": "09:15", "text": "Got it. I’ll help you reset access and confirm delivery settings."},
        ]
    if demo and st.session_state.get("demo_chat_autoplay") is None:
        st.session_state.demo_chat_autoplay = True

    # Parse backend strings ("Customer:" / "Agent:")
    msgs: List[dict] = []
    if conversation_history:
        t0 = time.strftime("%H:%M")
        for raw in conversation_history[-18:]:
            if raw.startswith("Customer:"):
                msgs.append({"role": "customer", "name": "Customer", "time": t0, "text": raw.replace("Customer:", "").strip()})
            elif raw.startswith("Agent:"):
                msgs.append({"role": "assistant", "name": "Agent", "time": t0, "text": raw.replace("Agent:", "").strip()})
            else:
                msgs.append({"role": "assistant", "name": "Agent", "time": t0, "text": str(raw)})
    else:
        msgs = list(st.session_state.demo_chat)

    wrap = st.container()
    with wrap:
        tab_conv, tab_trace = st.tabs(["Conversation", "AI Thinking Trace"])
        with tab_conv:
            st.markdown(
                """
                <div class="cc-card" style="padding:14px 14px;">
                  <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
                    <div style="font-weight:950; letter-spacing:-0.02em; font-size:16px;">Live conversation</div>
                    <div class="cc-pill"><span class="cc-dot cc-dot-blue"></span><span>Live</span></div>
                  </div>
                  <div style="height:10px;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for m in msgs:
                is_user = m["role"] == "customer"
                align = "flex-start" if is_user else "flex-end"
                bubble_bg = "rgba(255,255,255,.055)" if is_user else "rgba(59,130,246,.10)"
                bubble_border = "rgba(255,255,255,.10)" if is_user else "rgba(59,130,246,.22)"
                name = m.get("name", "—")
                tm = m.get("time", "")
                txt = (m.get("text") or "").replace("<", "&lt;").replace(">", "&gt;")
                avatar_bg = "rgba(245,158,11,.18)" if is_user else "rgba(59,130,246,.18)"
                avatar_txt = "C" if is_user else "AI"
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:{align}; margin-top:10px;">
                      <div style="max-width: 92%; display:flex; gap:10px; align-items:flex-end; flex-direction:{'row' if is_user else 'row-reverse'};">
                        <div style="width:32px; height:32px; border-radius:12px; background:{avatar_bg}; border:1px solid rgba(255,255,255,.10); display:flex; align-items:center; justify-content:center; font-weight:950;">
                          {avatar_txt}
                        </div>
                        <div style="padding:10px 12px; border-radius:16px; border:1px solid {bubble_border}; background:{bubble_bg}; box-shadow: 0 10px 26px rgba(0,0,0,.25);">
                          <div style="display:flex; gap:10px; justify-content:space-between; align-items:center;">
                            <div style="font-weight:900; font-size:12px; color:rgba(231,233,238,.78);">{name}</div>
                            <div style="font-size:11px; color:rgba(231,233,238,.55);">{tm}</div>
                          </div>
                          <div style="margin-top:6px; color:rgba(231,233,238,.92); line-height:1.35;">{txt}</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Typing indicator (set by execute handler)
            if float(st.session_state.get("typing_until", 0.0) or 0.0) > time.time():
                render_thinking_indicator(True, "AI typing")

            if demo:
                controls = st.columns([0.72, 0.28])
                with controls[0]:
                    st.caption("Demo mode: simulated customer + agent messages.")
                with controls[1]:
                    st.session_state.demo_chat_autoplay = st.toggle("Autoplay", value=bool(st.session_state.demo_chat_autoplay))

                if st.session_state.demo_chat_autoplay:
                    if st.button("Simulate next message", use_container_width=True, key="demo_chat_next"):
                        tnow = time.strftime("%H:%M")
                        script = [
                            ("customer", "Ava", "I checked spam — nothing there."),
                            ("assistant", "Agent", "Thanks. I’m going to verify the account email, then resend a reset link and confirm deliverability."),
                            ("assistant", "Agent", "If you use SSO, I’ll route you to the correct sign-in method to avoid reset loops."),
                        ]
                        idx = int(st.session_state.get("demo_chat_idx") or 0)
                        role, name, text = script[idx % len(script)]
                        st.session_state.demo_chat_idx = idx + 1
                        st.session_state.demo_chat.append({"role": role, "name": name, "time": tnow, "text": text})

        with tab_trace:
            # Show last action “trace” in a clean way
            if st.session_state.get("actions_history"):
                last = st.session_state.actions_history[-1]
                st.markdown(
                    "<div class='cc-card' style='padding:14px 14px;'><b>Latest trace</b></div>",
                    unsafe_allow_html=True,
                )
                with st.expander("Open trace", expanded=True):
                    st.write(f"Action: `{last.get('action_type')}`")
                    st.json(last.get("action_input") or {})
                    st.caption("Use the Actions panel to execute; trace updates per step.")
            else:
                st.info("No trace yet — execute an action to populate.")


def inject_keyboard_shortcuts() -> None:
    """
    Adds hackathon-friendly keyboard shortcuts:
    - R: Run (auto) / Execute (manual)
    - S: Stop
    - 1-6: quick-select actions
    """
    components.html(
        """
        <script>
        (function(){
          if (window.__cc_shortcuts_installed) return;
          window.__cc_shortcuts_installed = true;

          const clickButtonByText = (txt) => {
            const buttons = window.parent.document.querySelectorAll('button');
            for (const b of buttons) {
              const t = (b.innerText || '').trim();
              if (t === txt) { b.click(); return true; }
            }
            return false;
          };

          const actionMap = {
            '1': 'Classify',
            '2': 'Search KB',
            '3': 'Ask',
            '4': 'Respond',
            '5': 'Resolve',
            '6': 'Close'
          };

          window.parent.document.addEventListener('keydown', (e) => {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
            const k = (e.key || '').toLowerCase();
            if (k === 'r') { clickButtonByText('Execute'); clickButtonByText('Run'); }
            if (k === 's') { clickButtonByText('Stop'); }
            if (actionMap[e.key]) { clickButtonByText(actionMap[e.key]); }
          }, { capture: true });
        })();
        </script>
        """,
        height=0,
    )


def default_action_input(task_id: str, action_type: str) -> Dict[str, Any]:
    if action_type == "classify_ticket":
        if task_id == "medium_billing_missing_info":
            return {"issue_type": "billing_double_charge_missing_info"}
        if task_id == "hard_technical_troubleshooting":
            return {"issue_type": "technical_wifi_disconnect_troubleshooting"}
        return {"issue_type": "password_reset"}
    if action_type == "ask_customer_question":
        if task_id == "medium_billing_missing_info":
            return {"question_type": "billing", "question": "Can you share the invoice number?", "requested_info_key": "invoice_number"}
        if task_id == "hard_technical_troubleshooting":
            return {
                "question_type": "dns_settings",
                "question": "What are your DNS settings (Automatic or manual)?",
            }
        return {"question_type": "device_model", "question": "Which device model are you using?"}
    if action_type == "search_knowledge_base":
        if task_id == "easy_password_reset":
            return {"query": "forgot password reset link"}
        if task_id == "medium_billing_missing_info":
            return {"query": "double charge invoice refund duplicate billing"}
        if task_id == "hard_technical_troubleshooting":
            return {"query": "wifi disconnect forget network power-cycle router firmware DNS switch band"}
        return {"query": "relevant KB search query"}
    if action_type == "send_response":
        if task_id == "hard_technical_troubleshooting":
            return {
                "response": (
                    "Troubleshooting for Wi-Fi disconnects: forget the network and reconnect, power-cycle the router, "
                    "check router firmware, verify DNS settings, and try switching Wi-Fi band (2.4 vs 5 GHz)."
                )
            }
        if task_id == "medium_billing_missing_info":
            return {
                "response": (
                    "We will review the duplicate charge for your billing month using your invoice number, "
                    "verify both captures, and process a refund if confirmed duplicate."
                )
            }
        return {
            "response": (
                "Use Forgot password on the sign-in page, request a reset link, and set a new password from the email."
            )
        }
    if action_type == "confirm_customer_resolution":
        return {"customer_note": "Thanks — that fixed my issue. Please close the ticket."}
    if action_type == "resolve_ticket":
        if task_id == "hard_technical_troubleshooting":
            return {
                "resolution_summary": (
                    "Assisted with Wi-Fi disconnects after app update: provided steps to forget network, "
                    "power-cycle router, verify firmware, adjust DNS, and switch Wi-Fi band."
                )
            }
        if task_id == "medium_billing_missing_info":
            return {
                "resolution_summary": (
                    "Resolved duplicate billing using invoice details and billing month; refund initiated after verification."
                )
            }
        return {"resolution_summary": "Provided password reset steps using email reset link and new password."}
    if action_type == "close_ticket":
        return {}
    if action_type == "reopen_ticket":
        return {"reason": "The issue returned after the last resolution — please continue troubleshooting."}
    if action_type == "escalate_ticket":
        return {"reason": "Escalating for specialist review."}
    if action_type == "update_ticket_priority":
        return {"priority": "HIGH"}
    return {}


def auto_policy_actions(task_id: str) -> List[Dict[str, Any]]:
    """
    Deterministic policy identical to inference.py style.
    """
    if task_id == "easy_password_reset":
        return [
            {"action_type": "classify_ticket", "action_input": {"issue_type": "password_reset"}},
            {"action_type": "search_knowledge_base", "action_input": {"query": "forgot password reset link"}},
            {
                "action_type": "send_response",
                "action_input": {
                    "response": (
                        "To reset your password: go to the sign-in page, click 'Forgot password', "
                        "enter your account email, and use the reset link from your inbox. "
                        "Set a new password and if you don't receive the email within 10 minutes, "
                        "check spam or request again."
                    )
                },
            },
            {"action_type": "confirm_customer_resolution", "action_input": {"customer_note": "That worked — thank you."}},
            {"action_type": "resolve_ticket", "action_input": {"resolution_summary": "Provided password reset steps including using the reset link and setting a new password."}},
            {"action_type": "close_ticket", "action_input": {}},
        ]
    if task_id == "medium_billing_missing_info":
        return [
            {"action_type": "classify_ticket", "action_input": {"issue_type": "billing_double_charge_missing_info"}},
            {
                "action_type": "ask_customer_question",
                "action_input": {
                    "question_type": "billing",
                    "question": "Can you share the invoice number for the duplicate charge?",
                    "requested_info_key": "invoice_number",
                },
            },
            {"action_type": "search_knowledge_base", "action_input": {"query": "double charge invoice refund duplicate charge"}},
            {
                "action_type": "send_response",
                "action_input": {
                    "response": (
                        "Thanks. We'll investigate the duplicate charge for your billing month and process a refund. "
                        "Please ensure we use your invoice number to verify the two captures, confirm the duplicate capture, "
                        "and apply the refund accordingly."
                    )
                },
            },
            {"action_type": "confirm_customer_resolution", "action_input": {"customer_note": "Please proceed with the refund."}},
            {"action_type": "resolve_ticket", "action_input": {"resolution_summary": "Resolved by confirming the duplicate billing capture using invoice INV-20491 for the billing month of April and issuing a refund."}},
            {"action_type": "close_ticket", "action_input": {}},
        ]
    return [
        {"action_type": "classify_ticket", "action_input": {"issue_type": "technical_wifi_disconnect_troubleshooting"}},
        {
            "action_type": "ask_customer_question",
            "action_input": {
                "question_type": "dns_settings",
                "question": "What are your DNS settings (Automatic or manual)?",
            },
        },
        {
            "action_type": "ask_customer_question",
            "action_input": {
                "question_type": "router_firmware",
                "question": "Have you updated your router firmware recently?",
            },
        },
        {
            "action_type": "search_knowledge_base",
            "action_input": {"query": "wifi disconnect forget network power-cycle router firmware DNS switch band"},
        },
        {
            "action_type": "send_response",
            "action_input": {
                "response": (
                    "Try these troubleshooting steps for recurring Wi-Fi disconnects: "
                    "1) Forget the network and reconnect. "
                    "2) Power-cycle the router (unplug for 30 seconds). "
                    "3) Check that router firmware is up to date (router firmware). "
                    "4) Verify DNS settings (DNS): set to Automatic if possible or a reputable DNS. "
                    "5) Switch Wi-Fi band (2.4 GHz vs 5 GHz) if supported."
                )
            },
        },
        {"action_type": "confirm_customer_resolution", "action_input": {"customer_note": "I'll try those steps — thanks."}},
        {
            "action_type": "resolve_ticket",
            "action_input": {
                "resolution_summary": (
                    "Assisted the customer with Wi-Fi disconnects after the app update by providing troubleshooting steps: "
                    "forget the network, power-cycle the router, verify router firmware, adjust DNS settings, "
                    "and switch Wi-Fi band to improve stability."
                )
            },
        },
        {"action_type": "close_ticket", "action_input": {}},
    ]


def render_thinking_for_action(task_meta: Optional[TaskMeta], observation: Optional[dict], action_type: str, action_input: Dict[str, Any]) -> None:
    if not task_meta:
        show_ai_thinking(["No task metadata loaded."], "Planning trace: (no task)")
        return
    customer_preview = (observation or {}).get("customer_message", "") or ""
    customer_preview = customer_preview[:160] + ("…" if len(customer_preview) > 160 else "")
    status_now = (observation or {}).get("ticket_status", "—")
    tid = (observation or {}).get("ticket_id", "—")
    eid = (observation or {}).get("episode_id", "—")
    base = [
        "Context\n"
        f"  episode_id: {eid}\n"
        f"  ticket_id: {tid}\n"
        f"  task_id: {task_meta.task_id}\n"
        f"  ticket_status: {status_now}\n"
        f"  expected_issue_type: {task_meta.expected_issue_type}",
        f"Customer message (truncated)\n  {customer_preview}",
        f"Action\n  type: {action_type}\n  input keys: {list(action_input.keys()) if isinstance(action_input, dict) else []}",
    ]
    q = (action_input.get("query") if isinstance(action_input, dict) else "") or ""
    issue = (action_input.get("issue_type") if isinstance(action_input, dict) else "") or ""

    if action_type == "classify_ticket":
        base.append(
            "Intent — classify_ticket\n"
            f"  Submit issue_type={issue!r}; environment expects {task_meta.expected_issue_type!r}.\n"
            "  On match: ticket.issue_type set, status IN_PROGRESS, workflow advances."
        )
    elif action_type == "update_ticket_priority":
        pr = (action_input.get("priority") if isinstance(action_input, dict) else "") or ""
        base.append(f"Intent — update_ticket_priority\n  priority={pr!r} (LOW/MEDIUM/HIGH).")
    elif action_type == "ask_customer_question":
        base.append(
            "Intent — ask_customer_question\n"
            "  Collect billing invoice or hard-task diagnostics before KB search / send_response.\n"
            "  Medium task: correct requested_info_key moves ticket to WAITING_FOR_CUSTOMER."
        )
    elif action_type == "search_knowledge_base":
        base.append(
            "Intent — search_knowledge_base\n"
            f"  Query preview: {str(q)[:200]!r}\n"
            "  Matched articles populate observation.knowledge_base_results with relevance_score."
        )
    elif action_type == "send_response":
        base.append(
            "Intent — send_response\n"
            "  Requires prior KB match; response checked against task keyword list.\n"
            "  On success: ticket status WAITING_FOR_CONFIRMATION (customer must confirm before resolve)."
        )
    elif action_type == "confirm_customer_resolution":
        base.append(
            "Intent — confirm_customer_resolution\n"
            "  Only valid when status is WAITING_FOR_CONFIRMATION.\n"
            "  Simulates customer ack; clears gate → status IN_PROGRESS so resolve_ticket can run."
        )
    elif action_type == "resolve_ticket":
        base.append(
            "Intent — resolve_ticket\n"
            "  Blocked in WAITING_FOR_CONFIRMATION or WAITING_FOR_CUSTOMER.\n"
            "  Resolution text checked vs task keywords; success → RESOLVED."
        )
    elif action_type == "close_ticket":
        base.append("Intent — close_ticket\n  Requires ticket RESOLVED; then CLOSED.")
    elif action_type == "escalate_ticket":
        base.append("Intent — escalate_ticket\n  Handoff path; ticket ESCALATED, episode ends.")
    elif action_type == "reopen_ticket":
        base.append(
            "Intent — reopen_ticket\n  Only when ticket is RESOLVED (before close). "
            "Moves to REOPENED and rewinds workflow to send_response for a new customer-visible reply."
        )
    else:
        base.append(f"Intent — {action_type}\n  See environment workflow_policy for ordering.")

    header = f"Planning trace for action: {action_type}"
    show_ai_thinking(base, header)


def step_once(action_type: str, action_input: Dict[str, Any]) -> None:
    if not st.session_state.episode_id:
        st.error("No active episode. Click Reset first.")
        return
    if st.session_state.done:
        st.error("Episode already finished. Click Reset to start a new episode.")
        return

    payload = {"action_type": action_type, "action_input": action_input}

    # AI thinking shown before sending action (manual feel + transparency)
    task_meta = st.session_state.tasks_meta.get(st.session_state.task_id)
    render_thinking_for_action(task_meta, st.session_state.observation, action_type, action_input)

    with st.spinner(f"Sending action `{action_type}` to backend..."):
        resp = call_backend(
            "POST",
            "/step",
            json_payload={"episode_id": st.session_state.episode_id, "action": payload},
        )

    st.session_state.observation = resp.get("observation")
    st.session_state.reward = resp.get("reward")
    st.session_state.done = bool(resp.get("done", False))
    st.session_state.steps_taken += 1

    info = resp.get("info", {}) or {}
    # Persist time into each step's info so the Live Timeline page can show it.
    try:
        info["time_elapsed"] = float((st.session_state.observation or {}).get("time_elapsed", 0.0) or 0.0)
    except Exception:
        pass
    reward = st.session_state.reward or {}
    reason = reward.get("reason", "")

    st.session_state.actions_history.append(
        {
            "action_type": action_type,
            "action_input": action_input,
            "reward": reward,
            "info": info,
            "reason": reason,
        }
    )
    st.session_state.logs.append(
        f"{info.get('ticket_status', '')} | {action_type} | reward={reward.get('reward_score', 0.0):.2f} | {reason}".strip()
    )

    # When episode finishes, update episode history.
    if st.session_state.done:
        obs = st.session_state.observation or {}
        task_meta2 = st.session_state.tasks_meta.get(st.session_state.task_id)
        outcome = info.get("episode_outcome")
        success_closed = outcome == "success_closed"
        failure_ep = outcome in ("failure_budget", "failure_invalid_or_stuck", "escalated") or bool(info.get("truncated"))
        st.session_state.episode_history.append(
            {
                "task_id": st.session_state.task_id,
                "final_reward_score": float((reward or {}).get("reward_score", 0.0) or 0.0),
                "steps_taken": int(st.session_state.steps_taken),
                "closed": obs.get("ticket_status") == "CLOSED",
                "success_closed": success_closed,
                "failure_episode": failure_ep,
                "episode_outcome": outcome,
                "max_steps": int(task_meta2.max_steps) if task_meta2 else 0,
                "optimal_steps": int(task_meta2.optimal_steps) if task_meta2 else 0,
                "time_elapsed": float(obs.get("time_elapsed", 0.0) or 0.0),
            }
        )


def run_auto_mode() -> None:
    task_id = st.session_state.task_id
    if not st.session_state.episode_id:
        st.error("No active episode. Click Reset first.")
        return
    st.session_state.stop_auto = False

    actions = auto_policy_actions(task_id)
    for idx, a in enumerate(actions, start=1):
        if st.session_state.stop_auto:
            break
        if st.session_state.done:
            break
        step_once(a["action_type"], a.get("action_input", {}))
        # Small pacing so the UI feels “live”
        time.sleep(0.35)


def render_top_mission_header() -> None:
    """
    Top header (title + status + deploy) with subtle glass styling.
    """
    obs = st.session_state.get("observation") or {}
    ticket_status = str(obs.get("ticket_status") or "—")
    backend_ok = bool(st.session_state.get("tasks_meta"))
    if ticket_status in ("CLOSED", "RESOLVED"):
        dot_cls = "cc-dot-ok"
        status_label = "Healthy"
    elif ticket_status in ("ESCALATED", "REOPENED"):
        dot_cls = "cc-dot-bad"
        status_label = "Attention"
    elif ticket_status in ("IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_CONFIRMATION", "OPEN"):
        dot_cls = "cc-dot-warn"
        status_label = "Active"
    else:
        dot_cls = "cc-dot-warn"
        status_label = "Active"

    title_col, status_col, deploy_col = st.columns([0.62, 0.22, 0.16], vertical_alignment="center")
    with title_col:
        st.markdown(
            f"""
            <div class="cc-card" style="padding:14px 16px;">
              <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px;">
                <div>
                  <div style="font-size:22px; font-weight:950; letter-spacing:-0.02em;">
                    AI Customer Support Command Center
                  </div>
                  <div style="margin-top:6px; color:rgba(231,233,238,.72); font-weight:650;">
                    Real-time ops dashboard for AI-assisted ticket resolution
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with status_col:
        st.markdown(
            f"""
            <div class="cc-card" style="padding:14px 16px;">
              <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
                <div class="cc-pill" title="Live status">
                  <span class="cc-dot {dot_cls}"></span>
                  <span>{status_label}</span>
                </div>
                <div style="text-align:right;">
                  <div style="font-weight:900; font-size:12px; color:rgba(231,233,238,.72); letter-spacing:.06em; text-transform:uppercase;">Ticket</div>
                  <div style="font-weight:950; margin-top:4px;">{ticket_status}</div>
                </div>
              </div>
              <div style="margin-top:10px; color:rgba(231,233,238,.55); font-size:12px;">
                Backend: <code style="background:rgba(0,0,0,.24); padding:2px 8px; border-radius:10px; border:1px solid rgba(255,255,255,.08);">{BACKEND_BASE_URL}</code>
                <span style="margin-left:8px;">•</span>
                <span style="margin-left:8px; color:{'#10B981' if backend_ok else '#EF4444'}; font-weight:900;">
                  {"connected" if backend_ok else "offline"}
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with deploy_col:
        # “Deploy” is a UI affordance for hackathon demo; no real deployment hook here.
        deploy = st.button("Deploy", type="primary", use_container_width=True)
        if deploy:
            st.toast("Deploy queued (demo)")


def main() -> None:
    ensure_state()

    # Provide default session keys used by the new UI
    st.session_state.setdefault("demo_mode", False)
    st.session_state.setdefault("mode", "Manual")
    st.session_state.setdefault("task_id", "easy_password_reset")
    st.session_state.setdefault("stop_auto", False)
    st.session_state.setdefault("auto_running", False)
    st.session_state.setdefault("auto_plan", [])
    st.session_state.setdefault("auto_idx", 0)
    st.session_state.setdefault("typing_until", 0.0)

    backend_ok = bool(st.session_state.tasks_meta)

    # Minimal task metadata for demo/offline (so UI always looks alive)
    if (not backend_ok) and (not st.session_state.tasks_meta):
        st.session_state.tasks_meta = {
            "easy_password_reset": TaskMeta(
                task_id="easy_password_reset",
                label=TASK_LABELS["easy_password_reset"],
                difficulty="easy",
                sla_seconds=240,
                max_steps=7,
                optimal_steps=5,
                expected_issue_type="password_reset",
            ),
            "medium_billing_missing_info": TaskMeta(
                task_id="medium_billing_missing_info",
                label=TASK_LABELS["medium_billing_missing_info"],
                difficulty="medium",
                sla_seconds=360,
                max_steps=9,
                optimal_steps=7,
                expected_issue_type="billing_double_charge_missing_info",
            ),
            "hard_technical_troubleshooting": TaskMeta(
                task_id="hard_technical_troubleshooting",
                label=TASK_LABELS["hard_technical_troubleshooting"],
                difficulty="hard",
                sla_seconds=480,
                max_steps=12,
                optimal_steps=9,
                expected_issue_type="technical_wifi_disconnect_troubleshooting",
            ),
        }

    # ---------- Sticky top navigation (working pages) ----------
    def _get_query_params() -> Dict[str, List[str]]:
        try:
            qp = st.query_params  # Streamlit >= 1.30
            out: Dict[str, List[str]] = {}
            for k in qp:
                out[str(k)] = [str(x) for x in qp.get_all(k)]
            return out
        except Exception:
            qp = st.experimental_get_query_params()
            return {str(k): [str(x) for x in v] for k, v in qp.items()}

    def _set_query_params(**kwargs: str) -> None:
        try:
            st.query_params.clear()
            for k, v in kwargs.items():
                st.query_params[str(k)] = str(v)
        except Exception:
            st.experimental_set_query_params(**{str(k): str(v) for k, v in kwargs.items()})

    qp = _get_query_params()
    page = (qp.get("page", ["dashboard"])[0] or "dashboard").strip().lower()
    if page not in {"dashboard", "timeline", "reward", "settings"}:
        page = "dashboard"

    if (qp.get("deploy", ["0"])[0] or "0") == "1":
        st.toast("Deploy queued (demo)")
        _set_query_params(page=page)

    def _nav_link(label: str, target: str, active_page: str, extra_class: str = "") -> str:
        cls = "cc-active" if target == active_page else ""
        if extra_class:
            cls = f"{cls} {extra_class}".strip()
        return f"<a class='{cls}' href='?page={target}'>{label}</a>"

    st.markdown(
        f"""
        <div class="cc-topbar-wrap">
          <div class="cc-topbar">
            <div class="cc-navbar">
              <div style="display:flex; align-items:center; gap:12px;">
                <div class="cc-brand">
                  <div class="cc-brand-title">AI Support</div>
                  <div class="cc-brand-sub">Command Center</div>
                </div>
                <div class="cc-nav" style="flex:1;">
                  {_nav_link("Dashboard", "dashboard", page)}
                  {_nav_link("Live Timeline", "timeline", page)}
                  {_nav_link("Reward Intelligence", "reward", page)}
                  {_nav_link("Settings", "settings", page)}
                  <span class="cc-nav-spacer"></span>
                  <a class="cc-cta" href="?page={page}&deploy=1">Deploy</a>
                </div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    task_meta = st.session_state.tasks_meta.get(st.session_state.task_id)
    observation = st.session_state.observation or {}
    actions = st.session_state.actions_history or []

    # ----------------------------------------------------------
    # Live Auto Runner (backend): one step per rerun
    # ----------------------------------------------------------
    def _auto_tick_backend() -> None:
        if not st.session_state.get("auto_running"):
            return
        if st.session_state.get("stop_auto"):
            st.session_state.auto_running = False
            return
        if st.session_state.get("demo_mode"):
            # Demo mode uses its own simulator from Settings.
            st.session_state.auto_running = False
            return
        if not st.session_state.get("episode_id") or st.session_state.get("done"):
            st.session_state.auto_running = False
            return

        plan = list(st.session_state.get("auto_plan") or [])
        idx = int(st.session_state.get("auto_idx") or 0)
        if idx >= len(plan):
            st.session_state.auto_running = False
            return

        a = plan[idx] or {}
        action_type = str(a.get("action_type") or "")
        action_input = dict(a.get("action_input") or {})

        # Silent backend step (no thinking UI), so pages can live-refresh cleanly.
        resp = call_backend(
            "POST",
            "/step",
            json_payload={"episode_id": st.session_state.episode_id, "action": {"action_type": action_type, "action_input": action_input}},
        )

        st.session_state.observation = resp.get("observation")
        st.session_state.reward = resp.get("reward")
        st.session_state.done = bool(resp.get("done", False))
        st.session_state.steps_taken += 1

        info = resp.get("info", {}) or {}
        try:
            info["time_elapsed"] = float((st.session_state.observation or {}).get("time_elapsed", 0.0) or 0.0)
        except Exception:
            pass
        reward = st.session_state.reward or {}
        reason = reward.get("reason", "")

        st.session_state.actions_history.append(
            {"action_type": action_type, "action_input": action_input, "reward": reward, "info": info, "reason": reason}
        )

        st.session_state.auto_idx = idx + 1
        if st.session_state.done or st.session_state.auto_idx >= len(plan):
            st.session_state.auto_running = False

    # ==========================================================
    # PAGES
    # ==========================================================
    if page == "dashboard":
        _auto_tick_backend()
        render_top_mission_header()
        st.write("")

        # Quick links (keeps Dashboard/Settings/Reward interlinked)
        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("Open Settings", use_container_width=True):
                _set_query_params(page="settings")
                st.rerun()
        with q2:
            if st.button("Open Reward Intelligence", use_container_width=True):
                _set_query_params(page="reward")
                st.rerun()
        with q3:
            if st.button("Open Live Timeline", use_container_width=True):
                _set_query_params(page="timeline")
                st.rerun()
        st.write("")

        render_kpi_row(task_meta, observation, actions)
        st.write("")

        left, right = st.columns([0.68, 0.32], gap="large")
        with left:
            convo = observation.get("conversation_history", []) if observation else []
            render_chat_modern(convo, demo=bool(st.session_state.get("demo_mode")))
            st.write("")

            render_decision_flow_graph(st.session_state.task_id, actions, observation)
            st.write("")

            st.markdown(
                "<div class='cc-card' style='padding:10px 12px;'><b>Live Episode Timeline</b> is available on the <a href='?page=timeline'>Timeline</a> page.</div>",
                unsafe_allow_html=True,
            )
            st.write("")

            render_performance_analytics()

        with right:
            render_sla_visualizer(task_meta, observation)
            st.write("")
            render_reward_pie_compact(task_meta, observation, actions)
            st.write("")
            st.markdown(
                "<div class='cc-card' style='padding:10px 12px;'><b>Full details</b> are on the <a href='?page=reward'>Reward Intelligence</a> page.</div>",
                unsafe_allow_html=True,
            )

    elif page == "timeline":
        _auto_tick_backend()
        render_top_mission_header()
        st.write("")

        st.markdown("<div class='cc-card' style='padding:14px 14px;'><b>Live Episode Timeline</b></div>", unsafe_allow_html=True)
        st.caption("This page focuses only on the animated step-by-step episode timeline.")
        st.write("")

        max_steps = int((task_meta.max_steps if task_meta else 0) or 0)
        if not max_steps:
            st.info("No task loaded yet. Go to **Settings** → Reset / Start.")
        else:
            render_timeline(st.session_state.task_id, actions, max_steps)

    elif page == "reward":
        _auto_tick_backend()
        render_top_mission_header()
        st.write("")

        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("Open Dashboard", use_container_width=True):
                _set_query_params(page="dashboard")
                st.rerun()
        with q2:
            if st.button("Open Settings", use_container_width=True):
                _set_query_params(page="settings")
                st.rerun()
        with q3:
            if st.button("Open Live Timeline", use_container_width=True):
                _set_query_params(page="timeline")
                st.rerun()
        st.write("")

        st.markdown("<div class='cc-card' style='padding:14px 14px;'><b>Reward Intelligence</b></div>", unsafe_allow_html=True)
        running = bool(st.session_state.get("auto_running"))
        st.caption("Heuristic quality signals + environment rewards, for the current episode.")
        if running:
            st.info("Auto-run is in progress. This page will update live as each step completes.")
        st.write("")

        render_reward_intelligence_panel(task_meta, observation, actions)
        st.write("")
        render_environment_state_explainer(task_meta, observation)

    else:  # settings
        st.markdown("<div class='cc-card' style='padding:14px 14px;'><b>Settings</b></div>", unsafe_allow_html=True)
        st.write("")

        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("Open Dashboard", use_container_width=True):
                _set_query_params(page="dashboard")
                st.rerun()
        with q2:
            if st.button("Open Reward Intelligence", use_container_width=True):
                _set_query_params(page="reward")
                st.rerun()
        with q3:
            if st.button("Open Live Timeline", use_container_width=True):
                _set_query_params(page="timeline")
                st.rerun()
        st.write("")

        if not backend_ok:
            st.warning(
                "Backend not reachable. You can still demo the UI with **Demo mode**.\n\n"
                "To run backend:\n`uvicorn server.app:app --host 127.0.0.1 --port 8000`"
            )

        # Keep demo mode on when backend is unavailable, so the UI is never "dead".
        st.session_state.demo_mode = st.toggle(
            "Demo mode (no backend needed)",
            value=bool(st.session_state.get("demo_mode")) or (not backend_ok),
        )

        c_task, c_mode = st.columns([0.62, 0.38], vertical_alignment="center")
        with c_task:
            st.session_state.task_id = st.selectbox(
                "Activity / Task",
                options=list(TASK_LABELS.keys()),
                format_func=lambda k: TASK_LABELS.get(k, k),
                index=list(TASK_LABELS.keys()).index(st.session_state.task_id) if st.session_state.task_id in TASK_LABELS else 0,
            )
        with c_mode:
            st.session_state.mode = st.radio("Mode", ["Manual", "AI Auto"], index=0, horizontal=True)

        b1, b2, b3 = st.columns([0.34, 0.33, 0.33])
        with b1:
            start_reset = st.button("Reset / Start", type="primary", use_container_width=True)
        with b2:
            run_btn = st.button("Run", use_container_width=True)
        with b3:
            stop_btn = st.button("Stop", use_container_width=True)

        if stop_btn:
            st.session_state.stop_auto = True
            st.session_state.auto_running = False

        if start_reset:
            st.session_state.stop_auto = False
            st.session_state.auto_running = False
            st.session_state.auto_plan = []
            st.session_state.auto_idx = 0
            st.session_state.steps_taken = 0
            st.session_state.actions_history = []
            st.session_state.logs = []
            st.session_state.reward = None
            st.session_state.done = False

            if st.session_state.demo_mode:
                st.session_state.episode_id = f"DEMO-{random.randint(1000, 9999)}"
                demo_task = str(st.session_state.task_id or "easy_password_reset")
                if demo_task == "medium_billing_missing_info":
                    msg = "I was charged twice. I don’t have the invoice number right now."
                elif demo_task == "hard_technical_troubleshooting":
                    msg = "Wi‑Fi keeps disconnecting after the latest update."
                else:
                    msg = "Hi — I can’t log in. Reset email never arrives."

                st.session_state.observation = {
                    "episode_id": st.session_state.episode_id,
                    "ticket_id": f"TKT-{random.randint(1100, 9900)}",
                    "ticket_priority": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "ticket_status": "OPEN",
                    "customer_message": msg,
                    "conversation_history": [f"Customer: {msg}"],
                    "knowledge_base_results": [],
                    "time_elapsed": float(random.randint(5, 45)),
                }
            else:
                resp = call_backend("POST", "/reset", json_payload={"task_id": st.session_state.task_id})
                st.session_state.episode_id = resp.get("episode_id")
                st.session_state.observation = resp.get("observation")
                st.session_state.done = bool(resp.get("done", False))

            _set_query_params(page="dashboard")
            st.rerun()

        if run_btn:
            if st.session_state.demo_mode:
                def _demo_apply_action(action_type: str, action_input: Dict[str, Any]) -> None:
                    obs = st.session_state.get("observation") or {}
                    convo = list(obs.get("conversation_history") or [])
                    kb_results = list(obs.get("knowledge_base_results") or [])

                    # Lightly simulate state transitions so the stage UI behaves.
                    if action_type == "classify_ticket":
                        obs["ticket_status"] = "IN_PROGRESS"
                        convo.append("Agent: I’m classifying your issue to route it correctly.")
                    elif action_type == "search_knowledge_base":
                        obs["ticket_status"] = "IN_PROGRESS"
                        q = str(action_input.get("query") or "support article")
                        kb_results = [
                            {
                                "kb_topic": q[:60],
                                "matched": True,
                                "relevance_score": 0.82,
                                "articles": [f"{q}\n- Step 1\n- Step 2\n- Step 3"],
                            }
                        ]
                        convo.append(f"Agent: Searching knowledge base for: {q}")
                    elif action_type == "ask_customer_question":
                        obs["ticket_status"] = "WAITING_FOR_CUSTOMER"
                        q = str(action_input.get("question") or "Can you share more details?")
                        convo.append(f"Agent: {q}")
                    elif action_type == "send_response":
                        obs["ticket_status"] = "WAITING_FOR_CONFIRMATION"
                        resp = str(action_input.get("response") or "Here’s what to try…")
                        convo.append(f"Agent: {resp}")
                    elif action_type == "confirm_customer_resolution":
                        obs["ticket_status"] = "RESOLVED"
                        note = str(action_input.get("customer_note") or "Yes, that worked.")
                        convo.append(f"Customer: {note}")
                    elif action_type == "resolve_ticket":
                        obs["ticket_status"] = "RESOLVED"
                        convo.append("Agent: Marking ticket as resolved.")
                    elif action_type == "close_ticket":
                        obs["ticket_status"] = "CLOSED"
                        convo.append("Agent: Closing the ticket. Thanks!")
                        st.session_state.done = True

                    obs["conversation_history"] = convo[-30:]
                    obs["knowledge_base_results"] = kb_results
                    obs["time_elapsed"] = float(obs.get("time_elapsed", 0.0) or 0.0) + 12.0
                    st.session_state.observation = obs

                plan = auto_policy_actions(str(st.session_state.task_id or "easy_password_reset"))
                if st.session_state.mode == "AI Auto":
                    # Demo auto: apply the whole policy quickly so the dashboard shows progress.
                    for a in plan:
                        _demo_apply_action(str(a.get("action_type") or ""), dict(a.get("action_input") or {}))
                        cur_obs = st.session_state.get("observation") or {}
                        cur_status = str(cur_obs.get("ticket_status") or "")
                        cur_time = float(cur_obs.get("time_elapsed", 0.0) or 0.0)
                        st.session_state.actions_history = list(st.session_state.actions_history or []) + [
                            {
                                "action_type": a.get("action_type"),
                                "action_input": a.get("action_input", {}),
                                "reward": 0.0,
                                "info": {"demo": True, "ticket_status": cur_status, "time_elapsed": cur_time},
                            }
                        ]
                    st.success("Demo auto-run complete.")
                else:
                    # Demo manual: apply one next policy step.
                    next_step = plan[min(len(plan) - 1, int(len(st.session_state.actions_history or [])))] if plan else None
                    if next_step:
                        _demo_apply_action(str(next_step.get("action_type") or ""), dict(next_step.get("action_input") or {}))
                        cur_obs = st.session_state.get("observation") or {}
                        cur_status = str(cur_obs.get("ticket_status") or "")
                        cur_time = float(cur_obs.get("time_elapsed", 0.0) or 0.0)
                        st.session_state.actions_history = list(st.session_state.actions_history or []) + [
                            {
                                "action_type": next_step.get("action_type"),
                                "action_input": next_step.get("action_input", {}),
                                "reward": 0.0,
                                "info": {"demo": True, "ticket_status": cur_status, "time_elapsed": cur_time},
                            }
                        ]
                _set_query_params(page="dashboard")
                st.rerun()
            else:
                if st.session_state.mode == "AI Auto":
                    st.session_state.auto_plan = auto_policy_actions(str(st.session_state.task_id or "easy_password_reset"))
                    st.session_state.auto_idx = 0
                    st.session_state.auto_running = True
                else:
                    step_once(str(st.session_state.get("selected_action_type") or "classify_ticket"), {})
                _set_query_params(page="dashboard")
                st.rerun()


if __name__ == "__main__":
    main()

