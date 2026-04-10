"""
Abstract base task class for SRE Incident Response environment.
All task implementations must extend this class.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from graders.base_grader import BaseGrader
from models import ActionModel, ObservationModel


class BaseTask(ABC):
    """
    Abstract base class for all SRE incident response tasks.
    Subclasses must implement all abstract methods for scenario-specific logic.
    """

    def __init__(self) -> None:
        self.current_step: int = 0
        self.done: bool = False
        self.action_history: List[Tuple[str, str]] = []
        self.time_elapsed: float = 0.0
        self.grader: Optional[BaseGrader] = None

    @property
    @abstractmethod
    def task_id(self) -> str:
        """Unique task identifier."""
        ...

    @property
    @abstractmethod
    def task_name(self) -> str:
        """Human-readable task name."""
        ...

    @property
    @abstractmethod
    def difficulty(self) -> str:
        """Task difficulty: easy, medium, or hard."""
        ...

    @property
    @abstractmethod
    def max_steps(self) -> int:
        """Maximum steps allowed in this episode."""
        ...

    @property
    @abstractmethod
    def scenario_name(self) -> str:
        """Descriptive scenario name."""
        ...

    @abstractmethod
    def get_initial_observation(self) -> ObservationModel:
        """Generate the initial observation when the episode starts."""
        ...

    @abstractmethod
    def process_action(self, action: ActionModel) -> Tuple[ObservationModel, str]:
        """
        Process an agent action and return updated observation + feedback message.

        Args:
            action: The action taken by the agent.

        Returns:
            Tuple of (updated observation, feedback message).
        """
        ...

    @abstractmethod
    def create_grader(self) -> BaseGrader:
        """Create and return the task-specific grader instance."""
        ...

    def reset(self) -> ObservationModel:
        """Reset the task state for a new episode."""
        self.current_step = 0
        self.done = False
        self.action_history = []
        self.time_elapsed = 0.0
        self.grader = self.create_grader()
        return self.get_initial_observation()

    def step(self, action: ActionModel) -> Dict[str, Any]:
        """
        Execute one step: process action, grade it, update state.

        Args:
            action: The action taken by the agent.

        Returns:
            Dict with observation, reward, done, success, info.
        """
        if self.done:
            obs = self.get_initial_observation()
            obs.current_step = self.current_step
            obs.hint = "Episode already ended. Call /reset to start a new episode."
            return {
                "observation": obs,
                "reward": self.grader.total_reward if self.grader else 0.0,
                "done": True,
                "success": self.grader.total_reward >= 0.5 if self.grader else False,
                "info": {
                    "message": "Episode already ended",
                    "grader_breakdown": self.grader.breakdown if self.grader else {},
                },
            }

        self.current_step += 1
        self.time_elapsed += 15.0  # Simulate 15 seconds per step

        # Validate action type
        valid_actions = self.get_available_actions()
        if action.action_type not in valid_actions:
            obs = self.get_initial_observation()
            obs.current_step = self.current_step
            obs.time_elapsed_seconds = self.time_elapsed
            obs.hint = f"Invalid action_type '{action.action_type}'. Valid: {valid_actions}"
            return {
                "observation": obs,
                "reward": self.grader.total_reward if self.grader else 0.0,
                "done": False,
                "success": False,
                "info": {"error": "invalid action_type"},
            }

        # Record action
        self.action_history.append((action.action_type, action.value))

        # Process action and get observation
        observation, feedback = self.process_action(action)
        observation.current_step = self.current_step
        observation.time_elapsed_seconds = self.time_elapsed

        # Grade the action
        if self.grader is None:
            self.grader = self.create_grader()

        grade_message = self.grader.evaluate_action(
            action.action_type, action.value, self.action_history
        )

        # Apply penalties
        self._apply_penalties(action)

        # Check for episode end
        reward = self.grader.total_reward
        if self.grader.is_complete() or self.current_step >= self.max_steps:
            self.done = True

        success = reward >= 0.5 if self.done else False

        # Set hint in observation
        if feedback:
            observation.hint = feedback
        elif grade_message:
            observation.hint = grade_message

        return {
            "observation": observation,
            "reward": reward,
            "done": self.done,
            "success": success,
            "info": {
                "step": self.current_step,
                "action_type": action.action_type,
                "action_value": action.value,
                "grade_message": grade_message,
                "grader_breakdown": self.grader.breakdown,
                "reward_detail": self.grader.get_reward_model_dict(),
            },
        }

    def _apply_penalties(self, action: ActionModel) -> None:
        """Apply standard penalties based on action context."""
        if self.grader is None:
            return

        # Penalty: noop after step 5
        if action.action_type == "noop" and self.current_step > 5:
            self.grader.apply_penalty(0.02, f"noop action at step {self.current_step} (after step 5)")

        # Penalty: escalate when reward > 0.5
        if action.action_type == "escalate" and self.grader.total_reward > 0.5:
            self.grader.apply_penalty(0.05, "escalate when solution is likely known (reward > 0.5)")

    def get_available_actions(self) -> List[str]:
        """Return list of valid action type strings."""
        return [
            "acknowledge_alert",
            "diagnose",
            "run_query",
            "apply_fix",
            "escalate",
            "write_postmortem",
            "noop",
        ]

    def get_state_dict(self, episode_id: str) -> Dict[str, Any]:
        """Return the current state as a dict for the StateModel."""
        return {
            "task_id": self.task_id,
            "episode_id": episode_id,
            "current_step": self.current_step,
            "total_reward": self.grader.total_reward if self.grader else 0.0,
            "done": self.done,
            "scenario_name": self.scenario_name,
            "grader_scores": self.grader.breakdown if self.grader else {},
        }
