from __future__ import annotations

"""
Episode grading: deterministic per-task functions over `GradingView` (from public state).
"""

from .grading_view import build_grading_view
from .models import EnvironmentState
from .task_graders import grade_from_view


def grade_episode(state: EnvironmentState) -> float:
    """
    Deterministic, reproducible score in [0.0, 1.0].
    Dispatches to task-specific programmatic graders (see `task_graders.py`).
    """
    view = build_grading_view(state)
    return max(0.0, min(1.0, float(grade_from_view(view))))
