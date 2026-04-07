# Meta-Hackaoth Project Guide

## 1) Project Overview
This project simulates a deterministic customer-support workflow environment for agent training/evaluation.

Core capabilities:
- Ticket classification
- Knowledge-base search
- Customer follow-up questions
- Resolution + closure/escalation
- Step-wise reward shaping
- Deterministic grading for easy/medium/hard tasks
- FastAPI backend + Streamlit dashboard

## 2) Repository Structure
- `support_env/models.py` - typed Pydantic models
- `support_env/tasks.py` - task specs and deterministic customer responses
- `support_env/kb.py` - deterministic KB search
- `support_env/environment.py` - environment state machine (`reset`, `step`, `state`)
- `support_env/grader.py` - deterministic scoring in `[0.0, 1.0]`
- `server/app.py` - FastAPI endpoints
- `streamlit_app.py` - frontend dashboard
- `inference.py` - baseline deterministic runner with required log format
- `tests/` - unit/API tests
- `openenv.yaml` - environment manifest
- `Dockerfile` - container runtime

## 3) Prerequisites
- Python 3.10+ (3.11 recommended)
- pip
- (Optional) Docker Desktop

## 4) Installation
From project root:

```bash
pip install -r requirements.txt
```

## 5) Run Backend (FastAPI)
```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Health check:
```bash
curl http://localhost:8000/health
```

## 6) Run Frontend (Streamlit)
Default backend URL is `http://localhost:8000`.

```bash
streamlit run streamlit_app.py
```

Optional backend override:
- Environment variable: `BACKEND_BASE_URL`
- Or Streamlit secret: `BACKEND_BASE_URL`

## 7) API Reference

### `GET /health`
Returns service health.

### `GET /tasks`
Returns task metadata:
- `task_id`
- `label`
- `difficulty`
- `sla_seconds`
- `max_steps`
- `expected_issue_type`

### `POST /reset`
Start a new episode.

Body:
```json
{
  "task_id": "easy_password_reset",
  "seed": 123
}
```

Notes:
- `task_id` optional; if invalid, returns `400`.

### `POST /step`
Apply one action.

Body:
```json
{
  "episode_id": "<episode-id>",
  "action": {
    "action_type": "classify_ticket",
    "action_input": {
      "issue_type": "password_reset"
    }
  }
}
```

### `POST /state`
Body:
```json
{
  "episode_id": "<episode-id>"
}
```

### `GET /state?episode_id=<episode-id>`
Fetch current environment state.

## 8) Supported Action Types
- `classify_ticket`
- `ask_customer_question`
- `search_knowledge_base`
- `send_response`
- `resolve_ticket`
- `close_ticket`
- `escalate_ticket`
- `update_ticket_priority`

## 9) Baseline Inference
Run:
```bash
python inference.py
```

Optional env vars:
- `TASK_ID`
- `SEED`
- `API_BASE_URL`
- `MODEL_NAME`
- `OPENAI_API_KEY`
- `HF_TOKEN`

Logs are printed in required format:
- `[START]`
- `[STEP]`
- `[END]`

## 10) Testing
Run all tests:
```bash
pytest -q
```

Current coverage includes:
- Environment reset/step/state behavior
- Reward and grader correctness
- Episode termination
- Invalid action handling
- API endpoints (`/tasks`, `/reset`, `/state`)

## 11) Docker
Build:
```bash
docker build -t meta-hackaoth-env .
```

Run:
```bash
docker run -p 8000:8000 meta-hackaoth-env
```

## 12) Common Issues and Fixes

### A) Address already in use on port 8000
Another process is already bound to port `8000`.
- Stop the old process, then restart uvicorn.

### B) Streamlit cannot connect to backend
- Ensure backend is running at `http://localhost:8000`
- If different host/port, set `BACKEND_BASE_URL`

### C) Invalid action input in frontend
- `action_input` must be valid JSON object (`{...}`), not a list/string.

### D) Invalid task id
- `/reset` now validates and returns `400` for unknown task ids.

## 13) What Was Fixed in This QA Pass
- Added backend validation for invalid `task_id` in `POST /reset`
- Added/extended `GET /tasks` payload (`label`, metadata)
- Improved Streamlit backend URL handling to support environment variable + secrets
- Added Streamlit action `update_ticket_priority`
- Added validation that action input JSON must be an object
- Added API tests in `tests/test_api.py`
- Minor code cleanup (unused imports/variables)

## 14) What You Need to Replace in Codebase
If you are copying this into another repo, replace/add these files exactly:
- `server/app.py`
- `streamlit_app.py`
- `support_env/environment.py`
- `support_env/grader.py`
- `support_env/models.py`
- `requirements.txt`
- `tests/test_api.py`
- `PROJECT_GUIDE.md`

## 15) Recommended Daily Workflow
1. `pip install -r requirements.txt`
2. `pytest -q`
3. Start backend (`uvicorn ...`)
4. Start frontend (`streamlit run streamlit_app.py`)
5. Run one easy/medium/hard episode manually in UI
6. Run `python inference.py` for baseline sanity

# Meta-Hackaoth Project Guide

## 1) Project Overview
This project simulates a deterministic customer-support workflow environment for agent training/evaluation.

Core capabilities:
- Ticket classification
- Knowledge-base search
- Customer follow-up questions
- Resolution + closure/escalation
- Step-wise reward shaping
- Deterministic grading for easy/medium/hard tasks
- FastAPI backend + Streamlit dashboard

## 2) Repository Structure
- `support_env/models.py` - typed Pydantic models
- `support_env/tasks.py` - task specs and deterministic customer responses
- `support_env/kb.py` - deterministic KB search
- `support_env/environment.py` - environment state machine (`reset`, `step`, `state`)
- `support_env/grader.py` - deterministic scoring in `[0.0, 1.0]`
- `server/app.py` - FastAPI endpoints
- `streamlit_app.py` - frontend dashboard
- `inference.py` - baseline deterministic runner with required log format
- `tests/` - unit/API tests
- `openenv.yaml` - environment manifest
- `Dockerfile` - container runtime

## 3) Prerequisites
- Python 3.10+ (3.11 recommended)
- pip
- (Optional) Docker Desktop

## 4) Installation
From project root:

```bash
pip install -r requirements.txt
```

## 5) Run Backend (FastAPI)
```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Health check:
```bash
curl http://localhost:8000/health
```

## 6) Run Frontend (Streamlit)
Default backend URL is `http://localhost:8000`.

```bash
streamlit run streamlit_app.py
```

Optional backend override:
- Environment variable: `BACKEND_BASE_URL`
- Or Streamlit secret: `BACKEND_BASE_URL`

## 7) API Reference

### `GET /health`
Returns service health.

### `GET /tasks`
Returns task metadata:
- `task_id`
- `label`
- `difficulty`
- `sla_seconds`
- `max_steps`
- `expected_issue_type`

### `POST /reset`
Start a new episode.

Body:
```json
{
  "task_id": "easy_password_reset",
  "seed": 123
}
```

Notes:
- `task_id` optional; if invalid, returns `400`.

### `POST /step`
Apply one action.

Body:
```json
{
  "episode_id": "<episode-id>",
  "action": {
    "action_type": "classify_ticket",
    "action_input": {
      "issue_type": "password_reset"
    }
  }
}
```

### `POST /state`
Body:
```json
{
  "episode_id": "<episode-id>"
}
```

### `GET /state?episode_id=<episode-id>`
Fetch current environment state.

## 8) Supported Action Types
- `classify_ticket`
- `ask_customer_question`
- `search_knowledge_base`
- `send_response`
- `resolve_ticket`
- `close_ticket`
- `escalate_ticket`
- `update_ticket_priority`

## 9) Baseline Inference
Run:
```bash
python inference.py
```

Optional env vars:
- `TASK_ID`
- `SEED`
- `API_BASE_URL`
- `MODEL_NAME`
- `OPENAI_API_KEY`
- `HF_TOKEN`

Logs are printed in required format:
- `[START]`
- `[STEP]`
- `[END]`

## 10) Testing
Run all tests:
```bash
pytest -q
```

Current coverage includes:
- Environment reset/step/state behavior
- Reward and grader correctness
- Episode termination
- Invalid action handling
- API endpoints (`/tasks`, `/reset`, `/state`)

## 11) Docker
Build:
```bash
docker build -t meta-hackaoth-env .
```

Run:
```bash
docker run -p 8000:8000 meta-hackaoth-env
```

## 12) Common Issues and Fixes

### A) `Address already in use` on port 8000
Another process is already bound to port `8000`.
- Stop the old process, then restart uvicorn.

### B) Streamlit cannot connect to backend
- Ensure backend is running at `http://localhost:8000`
- If different host/port, set `BACKEND_BASE_URL`

### C) Invalid action input in frontend
- `action_input` must be valid JSON object (`{...}`), not a list/string.

### D) Invalid task id
- `/reset` now validates and returns `400` for unknown task ids.

## 13) What Was Fixed in This QA Pass
- Added backend validation for invalid `task_id` in `POST /reset`
- Added/extended `GET /tasks` payload (`label`, metadata)
- Improved Streamlit backend URL handling to support environment variable + secrets
- Added Streamlit action `update_ticket_priority`
- Added validation that action input JSON must be an object
- Added API tests in `tests/test_api.py`
- Minor code cleanup (unused imports/variables)

## 14) What You Need to Replace in Codebase
If you are copying this into another repo, replace/add these files exactly:
- `server/app.py`
- `streamlit_app.py`
- `support_env/environment.py`
- `support_env/grader.py`
- `support_env/models.py`
- `requirements.txt`
- `tests/test_api.py`
- `PROJECT_GUIDE.md`

## 15) Recommended Daily Workflow
1. `pip install -r requirements.txt`
2. `pytest -q`
3. Start backend (`uvicorn ...`)
4. Start frontend (`streamlit run streamlit_app.py`)
5. Run one easy/medium/hard episode manually in UI
6. Run `python inference.py` for baseline sanity

