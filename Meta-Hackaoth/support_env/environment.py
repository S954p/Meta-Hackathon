from __future__ import annotations

import secrets
from dataclasses import dataclass
from random import Random
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from .grader import grade_episode
from .kb import search_kb
from .models import (
    Action,
    ActionRecord,
    AgentState,
    Customer,
    CustomerScenario,
    EnvironmentState,
    Observation,
    Reward,
    Ticket,
)
from .tasks import TaskId, TASKS, get_task, deterministic_customer_response
from .workflow_policy import workflow_for_task


def _normalize_scenario(raw: Optional[str]) -> CustomerScenario:
    if not raw:
        return "cooperative"
    s = raw.strip().lower().replace("-", "_")
    aliases: dict[str, CustomerScenario] = {
        "default": "cooperative",
        "cooperative": "cooperative",
        "normal": "cooperative",
        "angry": "angry_customer",
        "angry_customer": "angry_customer",
        "silent": "silent_customer",
        "silent_customer": "silent_customer",
        "no_response": "silent_customer",
        "escalation": "escalation_hint",
        "escalation_hint": "escalation_hint",
        "supervisor": "escalation_hint",
    }
    return aliases.get(s, "cooperative")


def _kb_relevance_score(matched: bool, query: str, kb_topic: str, title: str = "") -> float:
    """Deterministic pseudo-confidence with visible variance (not a flat ~0.9 for every matched hit)."""
    q = (query or "").lower().replace("-", " ")
    topic_tokens = [t for t in (kb_topic or "").lower().replace("_", " ").split() if len(t) > 2]
    overlap = sum(1 for t in topic_tokens if t in q)
    # Wider spread: unmatched ~0.22–0.45, matched ~0.52–0.88
    base = 0.26 + (0.26 if matched else 0.0)
    overlap_b = min(0.22, 0.055 * overlap)
    q_density = min(0.14, len(q) / 900.0)
    title_b = min(0.12, 0.018 * len((title or "").split()))
    raw = base + overlap_b + q_density + title_b
    return round(max(0.18, min(0.92, raw)), 3)


@dataclass(frozen=True)
class _RewardContext:
    immediate_reward: float
    progress_score: float
    penalty_score: float
    reason: str


class SupportTicketEnvironment:
    """
    OpenEnv-like environment for a deterministic customer support workflow.
    """

    _STEP_PENALTY = 0.012

    def __init__(self) -> None:
        self._rng = Random(0)
        self._episode_id: str = ""
        self._task_id: TaskId = "easy_password_reset"
        self._task_spec = get_task(self._task_id)
        self._workflow_actions = workflow_for_task(self._task_id)
        self._time_per_action_seconds: float = 90.0
        self._max_invalid_actions: int = 3

        self._time_elapsed_seconds: float = 0.0
        self._done: bool = False
        self._invalid_action_count: int = 0

        self._ticket: Ticket = Ticket(ticket_id="T-0")
        self._customer: Customer = Customer(customer_id="C-0")
        self._agent_state: AgentState = AgentState()

        self._conversation_history: list[str] = []
        self._customer_response_ready: bool = False
        self._seed_used: Optional[int] = None
        self._episode_timeline: list[dict[str, Any]] = []
        self._workflow_index: int = 0
        self._last_reward_breakdown: Dict[str, Any] = {}
        self._silent_customer_ask_index: int = 0

    @property
    def used_seed(self) -> Optional[int]:
        return self._seed_used

    def reset(
        self,
        task_id: Optional[TaskId] = None,
        seed: Optional[int] = None,
        scenario: Optional[str] = None,
    ) -> Observation:
        if seed is not None:
            self._seed_used = int(seed)
            self._rng = Random(int(seed))
        else:
            # Non-fixed seed: varied episodes (HF / OpenAI / demos) without always using 0.
            self._seed_used = int.from_bytes(secrets.token_bytes(4), "big") % (2**31 - 1) or 1
            self._rng = Random(self._seed_used)

        self._episode_id = str(uuid4())
        # Ticket ID must be unique per episode even when seed is fixed (RNG would repeat).
        unique_ticket_suffix = uuid4().hex[:12].upper()

        # Ensure explicit task_id from UI always overrides seed-based selection.
        if task_id is not None:
            raw = str(task_id).strip()
            normalized_key = raw.lower().replace("_", " ").replace("-", " ")
            normalized_key = " ".join(normalized_key.split())

            # Support task ids, shorthand names, and common UI labels.
            alias_map = {
                "easy": "easy_password_reset",
                "medium": "medium_billing_missing_info",
                "hard": "hard_technical_troubleshooting",
                "easy password reset": "easy_password_reset",
                "medium billing missing info": "medium_billing_missing_info",
                "hard technical troubleshooting": "hard_technical_troubleshooting",
                "easy password_reset": "easy_password_reset",
                "medium billing_missing_info": "medium_billing_missing_info",
                "hard technical_troubleshooting": "hard_technical_troubleshooting",
            }

            # If UI sends labels like "Easy - Password Reset", map by keyword.
            if "easy" in normalized_key and "password" in normalized_key:
                normalized = "easy_password_reset"
            elif "medium" in normalized_key and "billing" in normalized_key:
                normalized = "medium_billing_missing_info"
            elif "hard" in normalized_key and "technical" in normalized_key:
                normalized = "hard_technical_troubleshooting"
            else:
                normalized = alias_map.get(normalized_key, raw)

            if normalized in TASKS:
                self._task_id = normalized  # type: ignore[assignment]
            else:
                raise ValueError(f"Unknown task_id: {task_id!r}")
        else:
            self._task_id = self._pick_task_deterministically()
        self._task_spec = get_task(self._task_id)
        self._workflow_actions = workflow_for_task(self._task_id)
        self._time_elapsed_seconds = 0.0
        self._done = False
        self._invalid_action_count = 0
        self._customer_response_ready = False
        self._silent_customer_ask_index = 0

        scen = _normalize_scenario(scenario)
        initial_msg = self._task_spec.initial_customer_message
        if scen == "escalation_hint":
            initial_msg = (
                f"{initial_msg} If this is not resolved quickly, I need a supervisor involved."
            )
        if scen == "angry_customer":
            initial_msg = f"I'm really upset about this — {initial_msg}"

        self._ticket = Ticket(
            ticket_id=f"T-{unique_ticket_suffix}",
            status="OPEN",
            priority=self._task_spec.default_priority,
            issue_type=None,
            resolution_notes=None,
        )
        self._customer = Customer(
            customer_id=f"C-{self._rng.randint(1000, 9999)}",
            customer_message=initial_msg,
            customer_satisfaction_score=0.35 if scen == "angry_customer" else 0.5,
            last_customer_response=None,
            scenario=scen,
        )
        self._agent_state = AgentState(step_count=0)

        self._conversation_history = [f"Customer: {self._customer.customer_message}"]
        self._episode_timeline = []
        self._workflow_index = 0
        self._last_reward_breakdown = {}

        return self._make_observation()

    def get_guidance(self) -> Dict[str, Any]:
        """Hints for model-driven loops (HF / OpenAI) without exposing private workflow rules."""
        return {
            "expected_next_action": self._expected_next_action(),
            "ticket_status": self._ticket.status,
            "workflow_step_index": self._workflow_index,
            "scenario": self._customer.scenario,
        }

    def _pick_task_deterministically(self) -> TaskId:
        # Deterministic “random” task selection.
        all_tasks: list[TaskId] = ["easy_password_reset", "medium_billing_missing_info", "hard_technical_troubleshooting"]
        idx = int(self._rng.random() * len(all_tasks)) % len(all_tasks)
        return all_tasks[idx]

    def _validate_action_semantics(self, action: Action) -> Tuple[bool, str]:
        t = action.action_type
        inp = action.action_input or {}
        if t == "classify_ticket":
            if not str(inp.get("issue_type") or inp.get("predicted_issue_type") or "").strip():
                return False, "classify_ticket requires issue_type (or predicted_issue_type)"
        elif t == "search_knowledge_base":
            if not str(inp.get("query") or inp.get("q") or "").strip():
                return False, "search_knowledge_base requires non-empty query"
        elif t == "ask_customer_question":
            qt = str(inp.get("question_type") or inp.get("diagnostic_key") or "").strip()
            q = str(inp.get("question") or inp.get("text") or "").strip()
            if not qt and not q:
                return False, "ask_customer_question requires question_type and/or question text"
        elif t == "send_response":
            if not str(inp.get("response") or inp.get("message") or inp.get("text") or "").strip():
                return False, "send_response requires response text"
        elif t == "resolve_ticket":
            if not str(
                inp.get("resolution_summary") or inp.get("resolution_notes") or inp.get("text") or ""
            ).strip():
                return False, "resolve_ticket requires resolution_summary (or resolution_notes)"
        elif t == "escalate_ticket":
            if not str(inp.get("reason") or inp.get("message") or "").strip():
                return False, "escalate_ticket requires reason (or message)"
        return True, ""

    def step(self, action: Any) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        if self._done:
            # If a client mistakenly continues, return done=True and minimal penalty.
            obs = self._make_observation()
            return obs, Reward(reward_score=0.0, progress_score=0.0, penalty_score=1.0, reason="Episode already done"), True, {
                "episode_id": self._episode_id
            }

        self._last_reward_breakdown = {}
        self._agent_state.step_count += 1
        self._time_elapsed_seconds += self._time_per_action_seconds

        # If we’re waiting for customer, advance deterministically at the next step.
        if self._ticket.status == "WAITING_FOR_CUSTOMER" and self._customer_response_ready:
            self._customer.customer_message = self._customer.last_customer_response or self._customer.customer_message
            self._ticket.status = "IN_PROGRESS"
            self._customer_response_ready = False

        parsed_action: Optional[Action] = None
        invalid_reason = ""
        try:
            parsed_action = Action.model_validate(action)
        except Exception as e:  # Pydantic validation
            invalid_reason = str(e)

        if parsed_action is not None:
            ok_sem, sem_err = self._validate_action_semantics(parsed_action)
            if not ok_sem:
                parsed_action = None
                invalid_reason = sem_err

        if parsed_action is None:
            self._invalid_action_count += 1
            self._done = self._invalid_action_count >= self._max_invalid_actions
            obs = self._make_observation()
            self._agent_state.last_action_type = None
            penalty_score = 0.7
            progress_score = self._compute_progress_score()
            return obs, Reward(
                reward_score=max(0.0, min(1.0, 0.0 - penalty_score)),
                progress_score=progress_score,
                penalty_score=penalty_score,
                reason=f"Invalid action: {invalid_reason}".strip(),
            ), self._done, {"episode_id": self._episode_id, "invalid_reason": invalid_reason}

        # Enforce task workflow order with a deterministic state machine.
        expected_action = self._expected_next_action()
        if not self._is_action_allowed(parsed_action.action_type):
            self._invalid_action_count += 1
            self._done = self._invalid_action_count >= self._max_invalid_actions
            obs = self._make_observation()
            progress_score = self._compute_progress_score()
            reward = Reward(
                reward_score=0.0,
                progress_score=progress_score,
                penalty_score=0.6,
                reason=(
                    f"Invalid action for workflow state: got '{parsed_action.action_type}', "
                    f"expected '{expected_action}'"
                ),
            )
            self._episode_timeline.append(
                {
                    "step": self._agent_state.step_count,
                    "action_type": parsed_action.action_type,
                    "action_input": parsed_action.action_input,
                    "reward_score": float(reward.reward_score),
                    "progress_score": float(reward.progress_score),
                    "penalty_score": float(reward.penalty_score),
                }
            )
            return obs, reward, self._done, {
                "episode_id": self._episode_id,
                "task_id": self._task_id,
                "ticket_status": self._ticket.status,
                "expected_action": expected_action,
                "expected_next_action": self._expected_next_action(),
            }

        # Track action history.
        self._agent_state.last_action_type = parsed_action.action_type
        self._agent_state.actions_taken.append(
            ActionRecord(action_type=parsed_action.action_type, action_input=parsed_action.action_input)
        )
        self._customer.customer_satisfaction_score = max(0.0, min(1.0, self._customer.customer_satisfaction_score))

        immediate_reward, progress_score, penalty_score, reason = self._apply_action_and_score(
            parsed_action.action_type, parsed_action.action_input
        )
        if parsed_action.action_type != "reopen_ticket" and (
            expected_action is not None and parsed_action.action_type == expected_action
        ):
            self._workflow_index = min(self._workflow_index + 1, len(self._workflow_actions))

        raw_score = max(0.0, min(1.0, immediate_reward - penalty_score))
        # Successful confirmation should stay visibly positive even under SLA stacking.
        if parsed_action.action_type == "confirm_customer_resolution" and "Customer confirmed" in reason:
            raw_score = max(raw_score, 0.12)
        reward = Reward(
            reward_score=raw_score,
            progress_score=progress_score,
            penalty_score=penalty_score,
            reason=reason,
        )

        # Record timeline for explainability/visualization.
        self._episode_timeline.append(
            {
                "step": self._agent_state.step_count,
                "action_type": parsed_action.action_type,
                "action_input": parsed_action.action_input,
                "reward_score": float(reward.reward_score),
                "progress_score": float(reward.progress_score),
                "penalty_score": float(reward.penalty_score),
            }
        )

        # Episode termination conditions.
        if self._ticket.status in ("CLOSED", "ESCALATED"):
            self._done = True
        truncated = False
        if self._agent_state.step_count >= self._task_spec.max_steps:
            self._done = True
            truncated = self._ticket.status not in ("CLOSED", "ESCALATED")
        obs = self._make_observation()
        outcome: Optional[str] = None
        if self._done:
            if self._ticket.status == "CLOSED":
                outcome = "success_closed"
            elif self._ticket.status == "ESCALATED":
                outcome = "escalated"
            elif truncated:
                outcome = "failure_budget"
            else:
                outcome = "failure_invalid_or_stuck"

        info = {
            "episode_id": self._episode_id,
            "task_id": self._task_id,
            "ticket_id": self._ticket.ticket_id,
            "ticket_status": self._ticket.status,
            "partial_grader_score": self._partial_score_for_info(),
            "expected_next_action": self._expected_next_action(),
            "reward_breakdown": getattr(self, "_last_reward_breakdown", {}),
            "truncated": truncated,
            "episode_outcome": outcome,
        }
        return obs, reward, self._done, info

    def _partial_score_for_info(self) -> float:
        try:
            return grade_episode(self.state())
        except Exception:
            return 0.0

    def _apply_action_and_score(
        self, action_type: str, action_input: Dict[str, Any]
    ) -> Tuple[float, float, float, str]:
        penalty_score = 0.0
        immediate_reward = 0.0
        reason = ""

        # SLA-based time penalty.
        sla_penalty = 0.0
        if self._time_elapsed_seconds > self._task_spec.sla_seconds:
            sla_penalty = min(0.4, (self._time_elapsed_seconds - self._task_spec.sla_seconds) / self._task_spec.sla_seconds * 0.4)

        # Helpers.
        expected_issue_type = self._task_spec.expected_issue_type

        def contains_any(text: str, keywords: list[str], min_count: int = 1) -> bool:
            t = (text or "").lower()
            hits = 0
            for kw in keywords:
                if kw.lower() in t:
                    hits += 1
            return hits >= min_count

        if action_type == "classify_ticket":
            provided_issue = str(action_input.get("issue_type") or action_input.get("predicted_issue_type") or "")
            if provided_issue == expected_issue_type:
                self._ticket.issue_type = expected_issue_type
                self._ticket.status = "IN_PROGRESS"
                immediate_reward = 0.2
                reason = "Correct classification"
            else:
                penalty_score = 0.5
                reason = "Incorrect classification"

        elif action_type == "update_ticket_priority":
            priority = str(action_input.get("priority") or "")
            if priority in ("LOW", "MEDIUM", "HIGH"):
                self._ticket.priority = priority  # type: ignore[assignment]
                immediate_reward = 0.05
                reason = "Priority updated"
            else:
                penalty_score = 0.3
                reason = "Invalid priority"

        elif action_type == "search_knowledge_base":
            query = str(action_input.get("query") or action_input.get("q") or "")
            if not query.strip():
                penalty_score = 0.5
                reason = "Missing KB query"
            else:
                kb_articles = search_kb(query)
                matched = any(a.kb_topic == expected_issue_type for a in kb_articles)
                results: list[Any] = []
                for a in kb_articles:
                    rel = _kb_relevance_score(matched, query, a.kb_topic, title=a.title)
                    results.append(
                        {
                            "query": query,
                            "kb_topic": a.kb_topic,
                            "matched": matched,
                            "relevance_score": rel,
                            "articles": [a.title + "\n" + a.body],
                        }
                    )
                # Store typed KB results.
                from .models import KnowledgeBaseResult as KBResultModel

                kb_results = [KBResultModel(**r) for r in results]
                self._agent_state.knowledge_base_results.extend(kb_results)
                self._agent_state.seen_kb_queries.append(query)
                immediate_reward = 0.1 if matched else 0.05
                self._ticket.status = "IN_PROGRESS"
                reason = "Knowledge base searched"

        elif action_type == "ask_customer_question":
            question_type = str(action_input.get("question_type") or action_input.get("diagnostic_key") or "")
            requested_info_key = str(action_input.get("requested_info_key") or action_input.get("requested_info") or "")
            question_text = str(action_input.get("question") or action_input.get("text") or "")

            # Update conversation.
            if question_text.strip():
                self._conversation_history.append(f"Agent: {question_text.strip()}")

            silent_attempt = (
                self._silent_customer_ask_index if self._customer.scenario == "silent_customer" else 0
            )
            customer_response = deterministic_customer_response(
                self._task_id,
                question_type=question_type,
                requested_info_key=requested_info_key if requested_info_key else None,
                turn_index=self._agent_state.step_count,
                scenario=self._customer.scenario,
                silent_attempt=silent_attempt,
            )
            if self._customer.scenario == "silent_customer":
                self._silent_customer_ask_index += 1
            if self._customer.scenario == "angry_customer":
                self._customer.customer_satisfaction_score = max(
                    0.0, self._customer.customer_satisfaction_score - 0.07
                )

            self._customer.last_customer_response = customer_response
            if not (customer_response or "").strip():
                self._conversation_history.append("Customer: [No response yet.]")
                immediate_reward = 0.04
                reason = "Customer did not respond yet (silent mode — follow up)"
            else:
                self._customer.customer_message = customer_response
                self._conversation_history.append(f"Customer: {customer_response.strip()}")

            if (customer_response or "").strip() and self._task_id == "medium_billing_missing_info":
                if requested_info_key == "invoice_number":
                    self._agent_state.requested_info["invoice_number"] = customer_response
                    self._ticket.status = "WAITING_FOR_CUSTOMER"
                    self._customer_response_ready = True
                    immediate_reward = 0.15
                    reason = "Requested missing invoice information"
                else:
                    penalty_score = 0.3
                    reason = "Asked irrelevant billing question"
            elif self._task_id == "hard_technical_troubleshooting" and (customer_response or "").strip():
                if question_type.strip():
                    self._agent_state.diagnostic_answers[question_type.strip()] = customer_response
                immediate_reward = 0.1
                reason = "Diagnostic question processed"

        elif action_type == "send_response":
            response_text = str(action_input.get("response") or action_input.get("message") or action_input.get("text") or "")
            if response_text.strip():
                self._conversation_history.append(f"Agent: {response_text.strip()}")

            if self._ticket.issue_type is None:
                penalty_score = 0.2
                immediate_reward = 0.0
                reason = "Responded before classification"
            else:
                kb_used = len(self._agent_state.knowledge_base_results) > 0 and any(
                    r.matched for r in self._agent_state.knowledge_base_results
                )
                if not kb_used:
                    penalty_score = 0.3
                    immediate_reward = 0.0
                    reason = "Responded before using relevant knowledge base article"
                else:
                    # Helpful response heuristic based on task keywords (KB-aligned).
                    must_keywords = self._task_spec.send_response_must_include_keywords
                    min_hits = 2 if self._task_id == "hard_technical_troubleshooting" else max(1, len(must_keywords) // 4)
                    helpful = contains_any(response_text, must_keywords, min_count=min_hits)
                    if helpful:
                        immediate_reward = 0.25
                        reason = "Helpful response aligned with KB steps"
                    else:
                        immediate_reward = 0.05
                        penalty_score = 0.2
                        reason = "Response not aligned with KB troubleshooting steps"
                    self._ticket.status = "WAITING_FOR_CONFIRMATION"

        elif action_type == "confirm_customer_resolution":
            note = str(action_input.get("customer_note") or action_input.get("message") or "").strip()
            ack = note or "Thanks — that helped. I'm okay to close this out."
            if self._ticket.status != "WAITING_FOR_CONFIRMATION":
                penalty_score = 0.3
                immediate_reward = 0.0
                reason = "No customer confirmation pending"
            else:
                self._conversation_history.append(f"Customer: {ack}")
                # Clear confirmation gate; agent may resolve next (workflow expects IN_PROGRESS here).
                self._ticket.status = "IN_PROGRESS"
                immediate_reward = 0.15
                reason = "Customer confirmed proposed resolution"

        elif action_type == "resolve_ticket":
            resolution_text = str(
                action_input.get("resolution_summary") or action_input.get("resolution_notes") or action_input.get("text") or ""
            )
            self._conversation_history.append(f"Agent: Resolution submitted: {resolution_text.strip()}")

            if self._ticket.status == "WAITING_FOR_CUSTOMER":
                penalty_score = 0.4
                immediate_reward = 0.0
                reason = "Resolved before customer response"
            elif self._ticket.status == "WAITING_FOR_CONFIRMATION":
                penalty_score = 0.35
                immediate_reward = 0.0
                reason = "Resolve blocked: waiting for customer confirmation of the response"
            elif self._ticket.status in ("IN_PROGRESS", "REOPENED"):
                # Resolution correctness heuristic: keywords + ticket issue type.
                must = self._task_spec.send_response_must_include_keywords
                text_window = resolution_text + " " + " ".join(self._conversation_history[-3:])
                min_hits = 2
                if self._task_id == "hard_technical_troubleshooting":
                    # Hard task: require more troubleshooting anchors in the resolution.
                    min_hits = 3
                correct_keywords = contains_any(text_window, must, min_count=min_hits)
                if correct_keywords:
                    self._ticket.resolution_notes = resolution_text.strip() or "Resolution provided"
                    self._ticket.status = "RESOLVED"
                    immediate_reward = 0.4
                    reason = "Resolution accepted"
                else:
                    penalty_score = 0.5
                    immediate_reward = 0.05
                    reason = "Resolution unclear or incorrect"
            else:
                penalty_score = 0.35
                immediate_reward = 0.0
                reason = "Resolve not valid in current ticket status"

        elif action_type == "close_ticket":
            if self._ticket.status == "RESOLVED":
                self._ticket.status = "CLOSED"
                immediate_reward = 0.2
                reason = "Ticket closed"
            else:
                penalty_score = 0.4
                immediate_reward = 0.0
                reason = "Cannot close ticket before resolution"

        elif action_type == "reopen_ticket":
            reopen_note = str(action_input.get("reason") or action_input.get("customer_note") or "").strip()
            if self._ticket.status != "RESOLVED":
                penalty_score = 0.35
                immediate_reward = 0.0
                reason = "Reopen only allowed once ticket is RESOLVED (before close)"
            else:
                msg = reopen_note or "The issue came back after the proposed fix."
                self._conversation_history.append(f"Customer: Please reopen — {msg}")
                self._ticket.status = "REOPENED"
                self._ticket.resolution_notes = None
                try:
                    self._workflow_index = self._workflow_actions.index("send_response")
                except ValueError:
                    self._workflow_index = max(0, len(self._workflow_actions) - 4)
                immediate_reward = 0.08
                reason = "Ticket reopened; continue with updated customer-facing response"

        elif action_type == "escalate_ticket":
            self._ticket.status = "ESCALATED"
            # Escalation reduces score (but episode terminates).
            penalty_score = 0.2 + sla_penalty
            immediate_reward = 0.0
            reason = "Escalated to a human agent"

        else:
            penalty_score = 0.6
            immediate_reward = 0.0
            reason = "Unknown action"

        # Apply SLA + per-step penalty as part of penalty_score.
        penalty_score = min(1.0, max(0.0, penalty_score + sla_penalty + self._STEP_PENALTY))
        self._last_reward_breakdown = {
            "immediate_reward": round(float(immediate_reward), 4),
            "sla_penalty": round(float(sla_penalty), 4),
            "step_penalty": round(float(self._STEP_PENALTY), 4),
            "wrong_classification": bool(action_type == "classify_ticket" and "Incorrect" in reason),
        }
        progress_score = self._compute_progress_score()
        return immediate_reward, progress_score, penalty_score, reason

    def _workflow_next(self) -> Optional[str]:
        if self._workflow_index >= len(self._workflow_actions):
            return None
        return self._workflow_actions[self._workflow_index]

    def _expected_next_action(self) -> Optional[str]:
        """
        Next action from the task workflow, overlaid with ticket-state gates so clients
        (HF / OpenAI loops) do not rely on a purely fixed script.
        """
        nxt = self._workflow_next()
        if self._ticket.status == "OPEN" and self._ticket.issue_type is None:
            return "classify_ticket"
        if self._ticket.status == "WAITING_FOR_CONFIRMATION":
            return "confirm_customer_resolution"
        return nxt

    def _is_action_allowed(self, action_type: str) -> bool:
        # Escalation is always allowed as an emergency stop.
        if action_type == "escalate_ticket":
            return True
        # Priority update is operational and can happen any time.
        if action_type == "update_ticket_priority":
            return True
        if action_type == "reopen_ticket":
            return self._ticket.status == "RESOLVED"
        if self._ticket.status == "WAITING_FOR_CONFIRMATION" and action_type not in (
            "confirm_customer_resolution",
            "escalate_ticket",
            "update_ticket_priority",
        ):
            return False
        expected = self._expected_next_action()
        if expected is None:
            return action_type in ("close_ticket", "escalate_ticket")
        return action_type == expected

    def _compute_progress_score(self) -> float:
        """
        Workflow progress in [0.0, 1.0] based on required actions.
        """
        required = list(self._task_spec.required_actions)
        if not required:
            return 0.0

        actual = [a.action_type for a in self._agent_state.actions_taken]
        # Count-based matching supports duplicate steps (hard task).
        from collections import Counter

        req_counts = Counter(required)
        act_counts = Counter(actual)
        matched = sum(min(req_counts[k], act_counts.get(k, 0)) for k in req_counts.keys())
        return float(matched) / float(len(required))

    def state(self) -> EnvironmentState:
        return EnvironmentState(
            episode_id=self._episode_id,
            task_id=self._task_id,
            time_elapsed_seconds=self._time_elapsed_seconds,
            step_count=self._agent_state.step_count,
            ticket=self._ticket,
            customer=self._customer,
            agent_state=self._agent_state,
            done=self._done,
            episode_timeline=list(self._episode_timeline),
        )

    def _make_observation(self) -> Observation:
        return Observation(
            episode_id=self._episode_id,
            ticket_id=self._ticket.ticket_id,
            customer_message=self._customer.customer_message,
            ticket_status=self._ticket.status,
            ticket_priority=self._ticket.priority,
            conversation_history=list(self._conversation_history),
            knowledge_base_results=list(self._agent_state.knowledge_base_results),
            time_elapsed=self._time_elapsed_seconds,
            actions_taken=[a.action_type for a in self._agent_state.actions_taken],
            customer_satisfaction_score=self._customer.customer_satisfaction_score,
            scenario=self._customer.scenario,
        )

