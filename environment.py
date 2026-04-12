# FIXED: [FIX 6] Added _initialized guard and better error recovery in step()
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

def _clamp_score(score: float) -> float:
    """
    Validator requires scores strictly between 0 and 1 (exclusive).
    0.0 and 1.0 are both invalid. Clamp to (0.001, 0.999).
    """
    return round(min(max(float(score), 0.001), 0.999), 4)



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
        self._initialized: bool = False
        self._last_observation: Optional[ObservationModel] = None
        self._total_reward: float = 0.001
        self._recent_actions: List[Tuple[str, str]] = []

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
        self._total_reward = 0.001
        self._initialized = True
        self._recent_actions = []

        # Reset the task and get initial observation
        observation = self.current_task.reset()
        self._last_observation = observation
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
        if not self._initialized:
            raise RuntimeError(
                "Environment not initialized. Call reset() first."
            )

        if self.current_task is None:
            raise RuntimeError(
                "No active episode. Call /reset with a task_id first."
            )

        # Guard: if episode already done, return final state without error
        if self.current_task.done and self._last_observation is not None:
            return StepResultModel(
                observation=self._last_observation,
                reward=_clamp_score(self._total_reward),
                done=True,
                success=self._total_reward >= 0.5,
                info={"error": "Episode already completed. Call /reset to start new episode."},
            )

        # Loop detection before task.step
        action_fingerprint = (
            action.action_type, 
            action.value[:50].lower().strip()
        )
        self._recent_actions.append(action_fingerprint)
        if len(self._recent_actions) > 3:
            self._recent_actions.pop(0)

        is_looping = (
            len(self._recent_actions) == 3 and
            len(set(self._recent_actions)) == 1
        )

        if is_looping:
            loop_penalty = 0.05
            self._total_reward = max(0.0, self._total_reward - loop_penalty)
            obs = self._last_observation
            
            # Manually increment step since we bypass task.step()
            self.current_task.current_step += 1
            obs.current_step = self.current_task.current_step
            
            obs.hint = (
                "LOOP DETECTED: You have repeated the same action 3 times "
                "with no reward change. Try a completely different action_type "
                f"or approach. Remaining steps: {obs.max_steps - obs.current_step}"
            )
            
            done = obs.current_step >= obs.max_steps
            if done: self.current_task.done = True
            
            return StepResultModel(
                observation=obs,
                reward=_clamp_score(self._total_reward),
                done=done,
                success=self._total_reward >= 0.5,
                info={
                    "step": obs.current_step,
                    "action_type": action.action_type,
                    "action_value": action.value,
                    "grade_message": "Loop detected — same action repeated 3 times",
                    "loop_penalty": loop_penalty,
                    "error": "loop_detected"
                }
            )

        previous_reward = self._total_reward
        result = self.current_task.step(action)

        # Track per-step reward
        self.step_rewards.append(result["reward"])
        self._total_reward = result["reward"]

        if self._total_reward > previous_reward:
            self._recent_actions = []

        step_result = StepResultModel(
            observation=result["observation"],
            reward=_clamp_score(result["reward"]),
            done=result["done"],
            success=result["success"],
            info=result["info"],
        )

        # Cache last observation for done-state guard
        self._last_observation = step_result.observation

        return step_result

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
