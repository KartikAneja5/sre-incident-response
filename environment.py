"""
SRE Environment: manages episode lifecycle, state, and task dispatch.
Thread-safe via episode_id tracking.
"""

import uuid
from typing import Any, Dict, List, Optional

from data.scenarios import get_all_task_info
from models import (
    ActionModel,
    ObservationModel,
    StateModel,
    StepResultModel,
    TaskInfo,
)
from tasks import TASK_REGISTRY
from tasks.base_task import BaseTask


class SREEnvironment:
    """
    Core environment class that manages the current episode.
    Supports reset, step, and state queries.
    Fully self-contained with no external dependencies.
    """

    def __init__(self) -> None:
        self.current_task: Optional[BaseTask] = None
        self.episode_id: str = ""
        self.task_id: str = ""
        self.step_rewards: List[float] = []

    def reset(self, task_id: str) -> ObservationModel:
        """
        Reset the environment for a new episode with the given task.

        Args:
            task_id: One of the registered task IDs.

        Returns:
            Initial observation for the task.

        Raises:
            ValueError: If task_id is not recognized.
        """
        if task_id not in TASK_REGISTRY:
            available = list(TASK_REGISTRY.keys())
            raise ValueError(
                f"Unknown task_id '{task_id}'. Available tasks: {available}"
            )

        # Create a fresh task instance
        task_class = TASK_REGISTRY[task_id]
        self.current_task = task_class()
        self.task_id = task_id
        self.episode_id = str(uuid.uuid4())
        self.step_rewards = []

        # Reset the task and get initial observation
        observation = self.current_task.reset()
        return observation

    def step(self, action: ActionModel) -> StepResultModel:
        """
        Execute one step in the environment.

        Args:
            action: The action to execute.

        Returns:
            StepResultModel with observation, reward, done, success, and info.

        Raises:
            RuntimeError: If no task is active (need to call /reset first).
        """
        if self.current_task is None:
            raise RuntimeError(
                "No active episode. Call /reset with a task_id first."
            )

        result = self.current_task.step(action)

        # Track per-step reward
        self.step_rewards.append(result["reward"])

        return StepResultModel(
            observation=result["observation"],
            reward=result["reward"],
            done=result["done"],
            success=result["success"],
            info=result["info"],
        )

    def get_state(self) -> StateModel:
        """
        Get the current environment state.

        Returns:
            StateModel with all current state information.

        Raises:
            RuntimeError: If no task is active.
        """
        if self.current_task is None:
            raise RuntimeError(
                "No active episode. Call /reset with a task_id first."
            )

        state_dict = self.current_task.get_state_dict(self.episode_id)
        return StateModel(**state_dict)

    def get_tasks(self) -> List[TaskInfo]:
        """
        Get information about all available tasks.

        Returns:
            List of TaskInfo objects.
        """
        tasks_data = get_all_task_info()
        return [TaskInfo(**t) for t in tasks_data]

    @property
    def is_active(self) -> bool:
        """Check if there is an active episode."""
        return self.current_task is not None

    @property
    def is_done(self) -> bool:
        """Check if the current episode is done."""
        if self.current_task is None:
            return True
        return self.current_task.done
