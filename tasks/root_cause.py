"""
Task 2: Root Cause Diagnosis (Medium) — max_steps=10
Payment service is down (HTTP 503). Bad deploy v2.4.1 introduced a slow SQL query,
which exhausted the DB connection pool, causing payment service to fail.
"""

from typing import Any, Dict, List, Tuple

from data.scenarios import (
    ROOT_CAUSE_ALERTS,
    ROOT_CAUSE_GOAL,
    ROOT_CAUSE_HINT,
    ROOT_CAUSE_LOGS,
    ROOT_CAUSE_METRICS,
    ROOT_CAUSE_QUERY_KEYWORDS,
    ROOT_CAUSE_QUERY_RESULTS,
)
from graders.base_grader import BaseGrader, matches_any
from models import ActionModel, ObservationModel
from tasks.base_task import BaseTask


class RootCauseDiagnosisGrader(BaseGrader):
    """
    Grader for the Root Cause Diagnosis task.

    Criteria (sum to 1.0):
    +0.20 → agent identifies the slow query
    +0.20 → agent links issue to deploy v2.4.1
    +0.20 → agent identifies connection pool exhaustion
    +0.20 → agent acknowledges correct root cause alert or payment-service alert
    +0.20 → agent suggests correct fix
    """

    CRITERIA = {
        "identify_slow_query": 0.20,
        "link_to_deploy": 0.20,
        "identify_pool_exhaustion": 0.20,
        "acknowledge_alert": 0.20,
        "suggest_fix": 0.20,
    }

    SLOW_QUERY_KEYWORDS = [
        "slow query", "slow sql", "query timeout", "long query",
        "47.3s", "47s", "slow queries", "query performance",
        "expensive query", "unoptimized query", "full table scan",
        "orders join customers", "orders join",
    ]

    DEPLOY_KEYWORDS = [
        "v2.4.1", "deploy", "deployment", "rollback", "version 2.4.1",
        "new release", "latest deploy", "recent deploy", "bad deploy",
        "deployed", "release v2.4.1", "2.4.1",
    ]

    POOL_KEYWORDS = [
        "connection pool", "pool exhausted", "connections", "pool full",
        "pool saturation", "connection exhaustion", "db connections",
        "490/500", "98% capacity", "pool usage", "connection limit",
        "no connection available", "pool timeout",
    ]

    ALERT_KEYWORDS = [
        "payment", "payment-service", "payment service", "503",
        "service down", "outage", "payment_service",
        "db-primary", "db primary", "database",
    ]

    FIX_KEYWORDS = [
        "rollback", "revert", "roll back", "kill query", "fix query",
        "optimize query", "add index", "revert deploy", "rollback deploy",
        "revert to v2.4.0", "rollback to v2.4.0", "rollback v2.4.1",
        "terminate query", "cancel query", "redeploy", "hotfix",
    ]

    def __init__(self) -> None:
        super().__init__(self.CRITERIA)

    def evaluate_action(self, action_type: str, value: str, action_history: List[Tuple[str, str]]) -> str:
        """Evaluate an action against all grading criteria."""
        messages = []
        val_lower = value.lower()

        # Check: acknowledge alert (payment or db-primary)
        if action_type == "acknowledge_alert":
            if matches_any(value, self.ALERT_KEYWORDS):
                if self.award("acknowledge_alert"):
                    messages.append("Correctly acknowledged the critical alert")

        # Check: identify slow query
        if action_type in ("diagnose", "run_query"):
            if matches_any(value, self.SLOW_QUERY_KEYWORDS):
                if self.award("identify_slow_query"):
                    messages.append("Identified the slow query as a contributing factor")

        # Check: link to deploy v2.4.1
        if action_type in ("diagnose", "run_query"):
            if matches_any(value, self.DEPLOY_KEYWORDS):
                if self.award("link_to_deploy"):
                    messages.append("Linked the issue to deploy v2.4.1")

        # Check: identify connection pool exhaustion
        if action_type in ("diagnose", "run_query"):
            if matches_any(value, self.POOL_KEYWORDS):
                if self.award("identify_pool_exhaustion"):
                    messages.append("Identified connection pool exhaustion")

        # Check: suggest fix
        if action_type in ("apply_fix", "diagnose"):
            if matches_any(value, self.FIX_KEYWORDS):
                if self.award("suggest_fix"):
                    messages.append("Suggested correct remediation action")

        # Comprehensive check for diagnose and postmortem actions
        if action_type in ("diagnose", "write_postmortem"):
            if matches_any(val_lower, self.SLOW_QUERY_KEYWORDS):
                self.award("identify_slow_query")
            if matches_any(val_lower, self.DEPLOY_KEYWORDS):
                self.award("link_to_deploy")
            if matches_any(val_lower, self.POOL_KEYWORDS):
                self.award("identify_pool_exhaustion")
            if matches_any(val_lower, self.FIX_KEYWORDS):
                self.award("suggest_fix")
            if matches_any(val_lower, self.ALERT_KEYWORDS):
                self.award("acknowledge_alert")

        # Penalty: apply_fix on wrong service when root cause not yet identified
        if action_type == "apply_fix":
            root_cause_found = (
                "identify_slow_query" in self.scored_criteria
                or "link_to_deploy" in self.scored_criteria
            )
            if not root_cause_found and not matches_any(value, self.DEPLOY_KEYWORDS + self.FIX_KEYWORDS):
                self.apply_penalty(0.05, "Applied fix before identifying root cause")

        return " | ".join(messages) if messages else "Action noted."


class RootCauseDiagnosisTask(BaseTask):
    """Task 2: Root Cause Diagnosis — Medium difficulty."""

    @property
    def task_id(self) -> str:
        return "root_cause_diagnosis"

    @property
    def task_name(self) -> str:
        return "Root Cause Diagnosis"

    @property
    def difficulty(self) -> str:
        return "medium"

    @property
    def max_steps(self) -> int:
        return 10

    @property
    def scenario_name(self) -> str:
        return "Root Cause Diagnosis — Bad Deploy and Slow Query"

    def create_grader(self) -> BaseGrader:
        return RootCauseDiagnosisGrader()

    def get_initial_observation(self) -> ObservationModel:
        return ObservationModel(
            logs=ROOT_CAUSE_LOGS,
            metrics=ROOT_CAUSE_METRICS,
            active_alerts=ROOT_CAUSE_ALERTS,
            task_goal=ROOT_CAUSE_GOAL,
            current_step=self.current_step,
            max_steps=self.max_steps,
            time_elapsed_seconds=self.time_elapsed,
            available_actions=self.get_available_actions(),
            hint=ROOT_CAUSE_HINT,
        )

    def _resolve_query(self, query_value: str) -> List[str]:
        """
        Resolve a run_query action to appropriate log results.
        Uses fuzzy keyword matching against the query value.
        """
        query_lower = query_value.lower()

        for result_key, keywords in ROOT_CAUSE_QUERY_KEYWORDS.items():
            if matches_any(query_lower, keywords):
                return ROOT_CAUSE_QUERY_RESULTS[result_key]

        return [f"No results found for query: '{query_value}'. Try: slow queries, deploy, connection pool, payment logs"]

    def process_action(self, action: ActionModel) -> Tuple[ObservationModel, str]:
        """Process an action and return updated observation with feedback."""
        feedback = ""
        obs = self.get_initial_observation()

        if action.action_type == "acknowledge_alert":
            if matches_any(action.value, RootCauseDiagnosisGrader.ALERT_KEYWORDS):
                feedback = (
                    "Alert acknowledged. Payment service is returning HTTP 503. "
                    "Success rate is 0%. Investigation needed to find root cause."
                )
            else:
                feedback = f"Alert acknowledgment noted for: {action.value}"

        elif action.action_type == "run_query":
            query_results = self._resolve_query(action.value)
            # Replace observation logs with query results for visibility
            obs.logs = query_results
            feedback = f"Query executed: {action.value}. Results returned in logs."

        elif action.action_type == "diagnose":
            feedback = f"Diagnosis recorded: {action.value[:300]}"

        elif action.action_type == "apply_fix":
            if matches_any(action.value, RootCauseDiagnosisGrader.FIX_KEYWORDS):
                feedback = (
                    "Fix applied. Initiating rollback to v2.4.0. "
                    "Slow query will be eliminated. Connection pool should recover in ~2 minutes."
                )
                # Update metrics to show improvement
                obs.metrics = {
                    "payment_success_rate": 85.0,
                    "db_connection_pool_usage": 45.0,
                    "db_slow_query_count": 0.0,
                    "payment_latency_p99_ms": 250.0,
                    "deploy_age_minutes": 0.0,
                    "db_queue_depth": 12.0,
                }
            else:
                feedback = f"Fix action noted: {action.value[:200]}"

        elif action.action_type == "escalate":
            feedback = f"Escalation recorded: {action.value[:200]}"

        elif action.action_type == "write_postmortem":
            feedback = "Postmortem recorded and saved."

        elif action.action_type == "noop":
            feedback = "No action taken. Consider investigating the root cause."

        obs.current_step = self.current_step
        obs.time_elapsed_seconds = self.time_elapsed
        return obs, feedback
