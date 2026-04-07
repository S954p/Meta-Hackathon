from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from support_env.environment import SupportTicketEnvironment
from support_env.tasks import TASKS


class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(default=None, description="easy_password_reset | medium_billing_missing_info | hard_technical_troubleshooting")
    seed: Optional[int] = None
    scenario: Optional[str] = Field(
        default=None,
        description="cooperative | angry_customer | silent_customer | escalation_hint",
    )


class StepRequest(BaseModel):
    episode_id: str
    action: Dict[str, Any]


class StateRequest(BaseModel):
    episode_id: str


_envs: Dict[str, SupportTicketEnvironment] = {}
_lock = Lock()


app = FastAPI(title="Meta-Hackaoth Support Ticket Environment")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
def tasks() -> Dict[str, Any]:
    """
    Required by the frontend spec.
    """
    payload = []
    for task_id, spec in TASKS.items():
        difficulty = (
            "easy" if "easy" in task_id else "medium" if "medium" in task_id else "hard" if "hard" in task_id else "unknown"
        )
        payload.append(
            {
                "task_id": spec.task_id,
                "label": spec.task_id.replace("_", " ").title(),
                "difficulty": difficulty,
                "sla_seconds": spec.sla_seconds,
                "max_steps": spec.max_steps,
                "optimal_steps": spec.optimal_steps,
                "expected_issue_type": spec.expected_issue_type,
            }
        )
    return {"tasks": payload}


@app.post("/reset")
def reset(req: ResetRequest) -> Dict[str, Any]:
    env = SupportTicketEnvironment()
    task_id = req.task_id if req.task_id else None
    try:
        obs = env.reset(task_id=task_id, seed=req.seed, scenario=req.scenario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task_id: {e}")
    # episode_id lives in env.state()
    state = env.state()
    with _lock:
        _envs[state.episode_id] = env
    return {
        "episode_id": state.episode_id,
        "observation": obs.model_dump(),
        "done": False,
        "info": {
            "task_id": state.task_id,
            "seed_used": env.used_seed,
            "scenario": state.customer.scenario,
        },
    }


@app.post("/step")
def step(req: StepRequest) -> Dict[str, Any]:
    with _lock:
        env = _envs.get(req.episode_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Unknown episode_id")
    obs, reward, done, info = env.step(req.action)
    return {
        "episode_id": req.episode_id,
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": info,
    }


@app.post("/state")
def state(req: StateRequest) -> Dict[str, Any]:
    with _lock:
        env = _envs.get(req.episode_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Unknown episode_id")
    return {"state": env.state().model_dump()}


@app.get("/state")
def state_get(episode_id: str) -> Dict[str, Any]:
    """
    Required by the frontend spec: GET /state.
    """
    with _lock:
        env = _envs.get(episode_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Unknown episode_id")
    return {"state": env.state().model_dump()}

