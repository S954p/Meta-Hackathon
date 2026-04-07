#!/usr/bin/env python3
"""
Baseline inference loop: local env, optional OpenAI, reproducible seed, trajectory JSONL.

Example:
  set SEED=123
  set TRAJECTORY_LOG_DIR=runs
  python baseline_inference.py

With OpenAI:
  set OPENAI_API_KEY=...
  set MODEL_NAME=gpt-4o-mini
  python baseline_inference.py --openai
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional

from support_env.environment import SupportTicketEnvironment
from support_env.grader import grade_episode
from support_env.tasks import get_task
from support_env.trajectory import TrajectoryLogger

TASK_IDS = [
    "easy_password_reset",
    "medium_billing_missing_info",
    "hard_technical_troubleshooting",
]


def _policy_action(task_id: str, observation: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic scripted fallback (same spirit as inference._make_policy_actions)."""
    from inference import _make_policy_actions

    policy = _make_policy_actions(task_id)
    taken = observation.get("actions_taken") or []
    idx = len(taken) if isinstance(taken, list) else 0
    if idx < len(policy):
        return policy[idx]
    return policy[-1]


def _openai_action(
    client: Any,
    model_name: str,
    task_id: str,
    observation: Dict[str, Any],
    guidance: Dict[str, Any],
) -> Dict[str, Any]:
    from inference import _build_single_action_prompt, _extract_json_payload, _parse_single_action

    prompt = _build_single_action_prompt(
        task_id,
        observation,
        max_steps=get_task(task_id).max_steps,
        step_index=len(observation.get("actions_taken") or []),
        guidance=guidance,
    )
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "Return strict JSON only. No markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=700,
    )
    content = (resp.choices[0].message.content or "").strip()
    data = _extract_json_payload(content)
    action = _parse_single_action(data)
    if action is None:
        raise ValueError("Model did not return a parseable action")
    return action


def run_episode(
    task_id: str,
    *,
    seed: int,
    scenario: Optional[str],
    use_openai: bool,
    model_name: str,
    logger: Optional[TrajectoryLogger],
) -> Dict[str, Any]:
    env = SupportTicketEnvironment()
    obs = env.reset(task_id=task_id, seed=seed, scenario=scenario)
    obs_dict = obs.model_dump()
    max_steps = get_task(task_id).max_steps
    total_shaped = 0.0
    steps: List[Dict[str, Any]] = []

    client = None
    if use_openai:
        from openai import OpenAI

        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY required for --openai")
        client = OpenAI(base_url=os.getenv("API_BASE_URL") or None, api_key=key)

    done = False
    for i in range(max_steps):
        if done:
            break
        guidance = env.get_guidance()
        if client is not None:
            try:
                action = _openai_action(client, model_name, task_id, obs_dict, guidance)
            except Exception:
                action = _policy_action(task_id, obs_dict)
        else:
            action = _policy_action(task_id, obs_dict)

        step_record = {
            "i": i,
            "action": action,
            "guidance": guidance,
            "observation_before": obs_dict,
        }
        obs, reward, done, info = env.step(action)
        obs_dict = obs.model_dump()
        total_shaped += float(reward.reward_score)
        step_record.update(
            {
                "reward": reward.model_dump(),
                "done": done,
                "info": info,
                "observation_after": obs_dict,
            }
        )
        steps.append(step_record)
        if logger:
            logger.log(
                {
                    "type": "step",
                    "task_id": task_id,
                    "seed": seed,
                    "scenario": scenario or "cooperative",
                    "episode_id": obs_dict.get("episode_id"),
                    **step_record,
                }
            )

    final_grade = grade_episode(env.state())
    summary = {
        "task_id": task_id,
        "seed": seed,
        "scenario": scenario or "cooperative",
        "used_seed": env.used_seed,
        "total_shaped_reward": round(total_shaped, 4),
        "final_grade": round(final_grade, 4),
        "steps": len(steps),
        "episode_outcome": (steps[-1]["info"] if steps else {}).get("episode_outcome"),
    }
    if logger:
        logger.log({"type": "episode_summary", **summary})
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description="Baseline benchmark runner with trajectory logging.")
    p.add_argument("--openai", action="store_true", help="Use OpenAI if key present; else policy.")
    p.add_argument("--model", default=os.getenv("MODEL_NAME", "gpt-4o-mini"))
    p.add_argument("--seed", type=int, default=int(os.getenv("SEED", "123")))
    p.add_argument(
        "--scenario",
        default=os.getenv("SCENARIO", "") or None,
        help="Customer scenario: cooperative | angry_customer | silent_customer | escalation_hint",
    )
    p.add_argument("--trajectory", default=os.getenv("TRAJECTORY_LOG_PATH", "") or None, help="JSONL file path")
    args = p.parse_args()

    if args.trajectory:
        logger: Optional[TrajectoryLogger] = TrajectoryLogger(args.trajectory)
    elif os.getenv("TRAJECTORY_LOG_DIR"):
        logger = TrajectoryLogger()
    else:
        logger = None

    results: List[Dict[str, Any]] = []
    for tid in TASK_IDS:
        row = run_episode(
            tid,
            seed=args.seed,
            scenario=args.scenario,
            use_openai=args.openai,
            model_name=args.model,
            logger=logger,
        )
        results.append(row)
        print(json.dumps(row, indent=2))

    mean_grade = sum(r["final_grade"] for r in results) / len(results)
    mean_shaped = sum(r["total_shaped_reward"] for r in results) / len(results)
    print("\n=== aggregate ===")
    print(json.dumps({"mean_final_grade": mean_grade, "mean_total_shaped_reward": mean_shaped, "seed": args.seed}, indent=2))


if __name__ == "__main__":
    main()
