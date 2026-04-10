"""
Base grader with fuzzy matching utilities for the SRE Incident Response environment.
All graders use keyword substring matching — never exact string matching.
"""

import re
from typing import Dict, List, Tuple


def matches_any(text: str, keywords: List[str]) -> bool:
    """
    Check if any keyword appears as a substring in the text (case-insensitive).
    This is the primary fuzzy matching function used by all graders.
    """
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def matches_any_regex(text: str, patterns: List[str]) -> bool:
    """
    Check if any regex pattern matches in the text (case-insensitive).
    Used for more complex matching like 'redis.*auth' patterns.
    """
    text_lower = text.lower()
    for pattern in patterns:
        try:
            if re.search(pattern.lower(), text_lower):
                return True
        except re.error:
            # If pattern is invalid regex, fall back to substring match
            if pattern.lower() in text_lower:
                return True
    return False


class BaseGrader:
    """
    Base grading engine that tracks per-criterion scores.
    Each criterion can only be scored once (no double-counting).
    Supports cumulative partial rewards and penalty application.
    """

    def __init__(self, criteria: Dict[str, float]):
        """
        Initialize the grader with named criteria and their weights.

        Args:
            criteria: Dict mapping criterion name to its weight (should sum to 1.0).
        """
        self.criteria = criteria
        self.scores: Dict[str, float] = {name: 0.0 for name in criteria}
        self.scored_criteria: set = set()
        self.penalties: float = 0.0
        self.penalty_log: List[str] = []

    def award(self, criterion: str, fraction: float = 1.0) -> bool:
        """
        Award score for a criterion. Can only be awarded once.

        Args:
            criterion: Name of the criterion to award.
            fraction: Fraction of the criterion weight to award (0.0 to 1.0).

        Returns:
            True if the criterion was newly awarded, False if already scored or invalid.
        """
        if criterion in self.scored_criteria:
            return False
        if criterion not in self.criteria:
            return False
        self.scores[criterion] = self.criteria[criterion] * min(1.0, max(0.0, fraction))
        self.scored_criteria.add(criterion)
        return True

    def apply_penalty(self, amount: float, reason: str) -> None:
        """Apply a penalty (positive number). Total reward will not go below 0."""
        self.penalties += abs(amount)
        self.penalty_log.append(f"-{abs(amount):.2f}: {reason}")

    @property
    def total_reward(self) -> float:
        """Calculate total reward: sum of scores minus penalties, clamped to (0, 1) exclusive."""
        raw = sum(self.scores.values()) - self.penalties
        # Validator requires strictly between 0 and 1 (not 0.0 and not 1.0)
        clamped = max(0.0, min(1.0, raw))
        if clamped <= 0.0:
            return 0.01
        if clamped >= 1.0:
            return 0.99
        return clamped

    @property
    def breakdown(self) -> Dict[str, float]:
        """Return a copy of the per-criterion scores."""
        result = dict(self.scores)
        if self.penalties > 0:
            result["penalties"] = -self.penalties
        return result

    def get_message(self) -> str:
        """Generate a human-readable summary of the current reward state."""
        lines = []
        for name, weight in self.criteria.items():
            score = self.scores[name]
            status = "✓" if name in self.scored_criteria else "○"
            lines.append(f"  {status} {name}: {score:.2f}/{weight:.2f}")
        for penalty_msg in self.penalty_log:
            lines.append(f"  ✗ Penalty {penalty_msg}")
        lines.append(f"  Total: {self.total_reward:.2f}")
        return "\n".join(lines)

    def is_complete(self, threshold: float = 0.95) -> bool:
        """Check if the total reward meets the completion threshold."""
        return self.total_reward >= threshold

    def get_reward_model_dict(self) -> Dict:
        """Return dict suitable for constructing a RewardModel."""
        return {
            "total": self.total_reward,
            "breakdown": self.breakdown,
            "message": self.get_message(),
        }

    def evaluate_action(self, action_type: str, value: str, action_history: List[Tuple[str, str]]) -> str:
        """
        Evaluate an action and update scores. Must be overridden by subclasses.

        Args:
            action_type: The type of action taken.
            value: The value/content of the action.
            action_history: List of (action_type, value) tuples from this episode.

        Returns:
            A message describing what happened.
        """
        raise NotImplementedError("Subclasses must implement evaluate_action")
