# Meta-Hackaoth Support Ticket Environment

## Environment Description
This project provides a production-grade, deterministic, OpenEnv-like environment that simulates real customer support workflows:
ticket classification, knowledge base search, asking for missing info/diagnostics, customer communication, resolution, ticket closure, and escalation.

The environment is designed to be suitable for RL agents, LLM agents, and workflow automation research.

## Motivation / Real-World Use Case
SaaS, banks, e-commerce, and telecom support teams rely on consistent ticket workflows:
identify the issue type, retrieve internal KB articles, request missing details, generate an appropriate response, and close or escalate tickets based on policy and SLA constraints.

## Action Space
Actions are represented with `SupportAction`:
`action_type` plus structured `action_input`.

Supported `action_type` values:
- `classify_ticket`
- `ask_customer_question`
- `search_knowledge_base`
- `send_response`
- `resolve_ticket`
- `close_ticket`
- `escalate_ticket`
- `update_ticket_priority`

## Observation Space
Observations are represented with `Observation` and include:
`ticket_id`, `customer_message`, `ticket_status`, `ticket_priority`,
`conversation_history`, `knowledge_base_results`, `time_elapsed`,
`actions_taken`, and `customer_satisfaction_score`.

## Reward Design
Rewards are step-wise and bounded:
- `reward_score` is always in `[0.0, 1.0]`
- `progress_score` measures workflow completion progress
- `penalty_score` measures rule/SLA violations
- `reason` explains the main reward signal

Positive step rewards are shaped for correct workflow order (classification, KB usage, asking questions, helpful response, resolution, and closure).

## Tasks (Difficulty Levels)
- `easy_password_reset` (Easy): password reset ticket
- `medium_billing_missing_info` (Medium): double-charge billing workflow that requires asking for invoice number
- `hard_technical_troubleshooting` (Hard): technical Wi-Fi troubleshooting requiring diagnostic questions and multi-step KB usage

Each task is graded by deterministic graders that return a reproducible score in `[0.0, 1.0]`.

## Setup (Local)
1. Install dependencies:
   - `pip install -r requirements.txt`
2. Run tests:
   - `pytest -q`

## Run the Server (Local)
`uvicorn server.app:app --host 0.0.0.0 --port 8000`

Endpoints:
- `GET /health`
- `POST /reset` (returns `episode_id`, `observation`)
- `POST /step` (requires `episode_id` and `action`)
- `POST /state` (returns full environment state)
- `GET /tasks` (tasks metadata)
- `GET /state?episode_id=...` (environment state for active episode)

## Docker
Build:
- `docker build -t meta-hackaoth-env .`

Run (Hugging Face–style: Streamlit on **7860** + API on **8000** inside the container):
- `docker run -p 7860:7860 meta-hackaoth-env`

Run (API only on port 8000):
- `docker run -p 8000:8000 -e PORT=8000 meta-hackaoth-env /app/scripts/run_api_only.sh`

## Hugging Face Spaces Deployment
Target Space (example): `https://huggingface.co/spaces/supriya028/my-chatbot`

1. Create or open the Space → choose **Docker** (this repo’s `Dockerfile` is meant for Spaces).
2. Push this repository to the Space (or connect GitHub and select the repo).
3. In Space **Settings** → set **Visibility** to **Public** so `https://huggingface.co/spaces/<user>/<name>` opens without login.
4. Optional **Space secrets / variables**: `OPENAI_API_KEY`, `API_URL`, `MODEL_NAME` (used by `inference.py` only; the dashboard uses the in-container API by default).

What runs in the container:
- **FastAPI** on `127.0.0.1:8000` (internal).
- **Streamlit** (`streamlit_command_center.py`) on `0.0.0.0:$PORT` (Hugging Face sets `PORT`, usually **7860**).  
  Streamlit talks to the API via `BACKEND_BASE_URL` (default `http://127.0.0.1:8000`).

If the Space shows **401** when opened in a private window, the Space is still **private** — make it **public** in Settings.

## Inference (Baseline)
Baseline runner: `inference.py`
It evaluates all 3 tasks (`easy`, `medium`, `hard`) with a reproducible seed and prints per-task final score plus average.

Example:
- `python inference.py`
- `SEED=123 python inference.py`
- `OPENAI_API_KEY=... MODEL_NAME=gpt-4o-mini python inference.py`
- `OPENAI_API_KEY=... API_URL=https://api.openai.com/v1 MODEL_NAME=gpt-4o-mini python inference.py`

Notes:
- **`inference.py` uses the OpenAI Python client only** (no Hugging Face Inference API path).
- Env vars: `OPENAI_API_KEY` (required for LLM calls), `API_URL` (default `https://api.openai.com/v1`), `MODEL_NAME` (default `gpt-4o-mini`), `SEED` (default `123`). If `OPENAI_API_KEY` is missing, the script falls back to deterministic actions (no LLM).
- Logs use **`[START]` / `[STEP]` / `[END]`** blocks per task.

## Testing Instructions
Run:
- `pytest -q`

## Streamlit Frontend Dashboard
Start the API first (Streamlit calls it on **Reset**):

`uvicorn server.app:app --host 127.0.0.1 --port 8000`

Then run the dashboard:

`streamlit run streamlit_command_center.py`

By default it calls the backend at `http://localhost:8000`. To change it, set:
- environment variable `BACKEND_BASE_URL` (or use `st.secrets` in Streamlit).

## Notes
This repo currently uses a deterministic, built-in knowledge base and deterministic customer responses so episodes and grading remain reproducible.

