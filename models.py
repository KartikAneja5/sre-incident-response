"""
Pydantic v2 models for the SRE Incident Response OpenEnv environment.
All models are fully typed and use Pydantic BaseModel.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ObservationModel(BaseModel):
    """Observation returned to the agent at each step."""

    logs: List[str] = Field(description="Last 10 relevant log lines")
    metrics: Dict[str, float] = Field(description="Service metrics (cpu, latency, error_rate etc)")
    active_alerts: List[str] = Field(description="Currently firing alerts with severity")
    task_goal: str = Field(description="What the agent must accomplish")
    current_step: int = Field(description="Step number in episode")
    max_steps: int = Field(description="Episode step limit")
    time_elapsed_seconds: float = Field(description="Simulated incident time")
    available_actions: List[str] = Field(description="List of valid action_type values")
    hint: Optional[str] = Field(default=None, description="Optional hint for debugging")


class ActionModel(BaseModel):
    """Action submitted by the agent."""

    action_type: str = Field(
        description="One of: acknowledge_alert, diagnose, run_query, apply_fix, escalate, write_postmortem, noop"
    )
    value: str = Field(description="The content/target of the action")


class RewardModel(BaseModel):
    """Detailed reward breakdown."""

    total: float = Field(description="Total cumulative reward 0.0 to 1.0")
    breakdown: Dict[str, float] = Field(description="Per-criterion partial scores")
    message: str = Field(description="Human readable reward reason")


class StepResultModel(BaseModel):
    """Result of taking a step in the environment."""

    observation: ObservationModel
    reward: float = Field(description="Cumulative partial reward 0.0 to 1.0")
    done: bool = Field(description="Whether the episode is over")
    success: bool = Field(description="Whether the task was completed successfully")
    info: Dict[str, Any] = Field(description="Grader breakdown, step details")


class StateModel(BaseModel):
    """Current environment state."""

    task_id: str
    episode_id: str
    current_step: int
    total_reward: float
    done: bool
    scenario_name: str
    grader_scores: Dict[str, float] = Field(description="Per-criterion scores")


class ResetRequest(BaseModel):
    """Request body for the /reset endpoint."""

    task_id: Optional[str] = Field(
        default=None, description="ID of the task to start"
    )


class TaskInfo(BaseModel):
    """Information about an available task."""

    id: str
    name: str
    difficulty: str
    max_steps: int
    description: str
