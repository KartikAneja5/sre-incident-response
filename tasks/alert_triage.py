"""
Task 1: Alert Triage (Easy) — max_steps=8
5 alerts firing simultaneously across a microservices stack.
Root cause: db-primary CPU at 98% causing cascading failures.
"""

from typing import Any, Dict, List, Tuple

from data.scenarios import (
    ALERT_TRIAGE_ALERTS,
    ALERT_TRIAGE_GOAL,
    ALERT_TRIAGE_HINT,
    ALERT_TRIAGE_LOGS,
    ALERT_TRIAGE_METRICS,
)
from graders.base_grader import BaseGrader, matches_any
from models import ActionModel, ObservationModel
from tasks.base_task import BaseTask


class AlertTriageGrader(BaseGrader):
    """
    Grader for the Alert Triage task.

    Criteria (sum to 1.0):
    +0.15 → agent acknowledges CRITICAL: db-primary alert first or as root cause
    +0.15 → agent correctly classifies db-primary alert as P1
    +0.10 → agent correctly classifies payment-service alert as P1
    +0.10 → agent correctly classifies auth-service alert as P2
    +0.10 → agent correctly classifies cache-redis alert as P2
    +0.10 → agent correctly classifies api-gateway alert as P3
    +0.15 → agent diagnoses "db CPU overload" or "db-primary" as root cause
    +0.15 → agent's diagnosis mentions cascading failure or downstream impact
    """

    CRITERIA = {
        "ack_db_primary": 0.15,
        "classify_db_p1": 0.15,
        "classify_payment_p1": 0.10,
        "classify_auth_p2": 0.10,
        "classify_cache_p2": 0.10,
        "classify_gateway_p3": 0.10,
        "diagnose_root_cause": 0.15,
        "diagnose_cascade": 0.15,
    }

    ROOT_CAUSE_KEYWORDS = [
        "db-primary", "database", "cpu", "db cpu", "primary db",
        "db primary", "database cpu", "db overload", "database overload",
        "db_primary", "db server",
    ]

    CASCADE_KEYWORDS = [
        "cascade", "cascading", "downstream", "propagat",
        "chain", "ripple", "domino", "knock-on", "secondary",
        "symptom", "caused by", "because of", "resulting from",
        "follow-on", "dependent", "upstream",
    ]

    DB_KEYWORDS = [
        "db-primary", "db_primary", "database", "db", "primary db",
        "db cpu", "db primary",
    ]
    PAYMENT_KEYWORDS = ["payment", "payment-service", "payment_service"]
    AUTH_KEYWORDS = ["auth", "auth-service", "auth_service", "authentication"]
    CACHE_KEYWORDS = ["cache", "redis", "cache-redis", "cache_redis"]
    GATEWAY_KEYWORDS = ["gateway", "api-gateway", "api_gateway", "api gateway"]

    P1_KEYWORDS = ["p1", "priority 1", "critical", "sev1", "sev 1", "highest", "urgent"]
    P2_KEYWORDS = ["p2", "priority 2", "warning", "sev2", "sev 2", "medium", "moderate", "high"]
    P3_KEYWORDS = ["p3", "priority 3", "info", "sev3", "sev 3", "low", "informational"]

    def __init__(self) -> None:
        super().__init__(self.CRITERIA)

    def evaluate_action(self, action_type: str, value: str, action_history: List[Tuple[str, str]]) -> str:
        """Evaluate an action against all grading criteria."""
        messages = []

        # Check: acknowledge db-primary alert (as root cause or first ack)
        if action_type == "acknowledge_alert":
            if matches_any(value, self.DB_KEYWORDS):
                if self.award("ack_db_primary"):
                    messages.append("Correctly acknowledged db-primary as critical root cause alert")

        # Check: classification actions
        if action_type in ("acknowledge_alert", "diagnose"):
            # db-primary as P1
            if matches_any(value, self.DB_KEYWORDS) and matches_any(value, self.P1_KEYWORDS):
                if self.award("classify_db_p1"):
                    messages.append("Correctly classified db-primary as P1")
            # Also award if they acknowledge db-primary with "critical" or "root cause"
            elif matches_any(value, self.DB_KEYWORDS) and matches_any(value, ["root cause", "root_cause", "primary cause"]):
                if self.award("classify_db_p1"):
                    messages.append("Correctly identified db-primary as P1 root cause")

            # payment-service as P1
            if matches_any(value, self.PAYMENT_KEYWORDS) and matches_any(value, self.P1_KEYWORDS):
                if self.award("classify_payment_p1"):
                    messages.append("Correctly classified payment-service as P1")

            # auth-service as P2
            if matches_any(value, self.AUTH_KEYWORDS) and matches_any(value, self.P2_KEYWORDS):
                if self.award("classify_auth_p2"):
                    messages.append("Correctly classified auth-service as P2")

            # cache-redis as P2
            if matches_any(value, self.CACHE_KEYWORDS) and matches_any(value, self.P2_KEYWORDS):
                if self.award("classify_cache_p2"):
                    messages.append("Correctly classified cache-redis as P2")

            # api-gateway as P3
            if matches_any(value, self.GATEWAY_KEYWORDS) and matches_any(value, self.P3_KEYWORDS):
                if self.award("classify_gateway_p3"):
                    messages.append("Correctly classified api-gateway as P3")

        # Check: root cause diagnosis
        if action_type == "diagnose":
            if matches_any(value, self.ROOT_CAUSE_KEYWORDS):
                if self.award("diagnose_root_cause"):
                    messages.append("Correctly diagnosed db-primary as root cause")

                # Also check for cascade in the same diagnosis
                if matches_any(value, self.CASCADE_KEYWORDS):
                    if self.award("diagnose_cascade"):
                        messages.append("Correctly identified cascading failure pattern")

        # Also check acknowledge_alert for root cause identification
        if action_type == "acknowledge_alert":
            combined = value.lower()
            if matches_any(combined, self.ROOT_CAUSE_KEYWORDS) and matches_any(combined, ["root cause", "root_cause", "primary cause", "main cause"]):
                if self.award("diagnose_root_cause"):
                    messages.append("Correctly identified root cause via acknowledgment")

        # Broad check: any action that mentions all classifications together
        if action_type in ("diagnose", "write_postmortem"):
            # Check if the value contains a comprehensive triage
            val_lower = value.lower()

            # Check individual classifications from comprehensive text
            if matches_any(val_lower, self.DB_KEYWORDS):
                if matches_any(val_lower, self.P1_KEYWORDS) or matches_any(val_lower, ["root cause", "primary"]):
                    self.award("classify_db_p1")
                    self.award("ack_db_primary")

            if matches_any(val_lower, self.PAYMENT_KEYWORDS):
                if matches_any(val_lower, self.P1_KEYWORDS):
                    self.award("classify_payment_p1")

            if matches_any(val_lower, self.AUTH_KEYWORDS):
                if matches_any(val_lower, self.P2_KEYWORDS) or "symptom" in val_lower:
                    self.award("classify_auth_p2")

            if matches_any(val_lower, self.CACHE_KEYWORDS):
                if matches_any(val_lower, self.P2_KEYWORDS) or "symptom" in val_lower:
                    self.award("classify_cache_p2")

            if matches_any(val_lower, self.GATEWAY_KEYWORDS):
                if matches_any(val_lower, self.P3_KEYWORDS) or "symptom" in val_lower:
                    self.award("classify_gateway_p3")

            if matches_any(val_lower, self.ROOT_CAUSE_KEYWORDS):
                self.award("diagnose_root_cause")

            if matches_any(val_lower, self.CASCADE_KEYWORDS):
                self.award("diagnose_cascade")

        # Penalty: apply_fix before root cause identified
        if action_type == "apply_fix" and "diagnose_root_cause" not in self.scored_criteria:
            self.apply_penalty(0.05, "Applied fix before identifying root cause")

        return " | ".join(messages) if messages else "Action noted."


class AlertTriageTask(BaseTask):
    """Task 1: Alert Triage — Easy difficulty."""

    @property
    def task_id(self) -> str:
        return "alert_triage"

    @property
    def task_name(self) -> str:
        return "Alert Triage"

    @property
    def difficulty(self) -> str:
        return "easy"

    @property
    def max_steps(self) -> int:
        return 8

    @property
    def scenario_name(self) -> str:
        return "Alert Triage — Cascading Failures from DB CPU Overload"

    def create_grader(self) -> BaseGrader:
        return AlertTriageGrader()

    def get_initial_observation(self) -> ObservationModel:
        return ObservationModel(
            logs=ALERT_TRIAGE_LOGS,
            metrics=ALERT_TRIAGE_METRICS,
            active_alerts=ALERT_TRIAGE_ALERTS,
            task_goal=ALERT_TRIAGE_GOAL,
            current_step=self.current_step,
            max_steps=self.max_steps,
            time_elapsed_seconds=self.time_elapsed,
            available_actions=self.get_available_actions(),
            hint=ALERT_TRIAGE_HINT,
        )

    def process_action(self, action: ActionModel) -> Tuple[ObservationModel, str]:
        """Process an action and return updated observation with feedback."""
        feedback = ""

        if action.action_type == "acknowledge_alert":
            if matches_any(action.value, AlertTriageGrader.DB_KEYWORDS):
                feedback = (
                    "Alert acknowledged: db-primary CPU > 95%. "
                    "This is the most critical alert. Database CPU at 98% "
                    "is likely the root cause of downstream failures."
                )
            elif matches_any(action.value, AlertTriageGrader.PAYMENT_KEYWORDS):
                feedback = (
                    "Alert acknowledged: payment-service error rate > 30%. "
                    "Payment service is experiencing connection timeouts to db-primary."
                )
            elif matches_any(action.value, AlertTriageGrader.AUTH_KEYWORDS):
                feedback = (
                    "Alert acknowledged: auth-service p99 latency > 800ms. "
                    "Authentication requests are slow but not failing completely."
                )
            elif matches_any(action.value, AlertTriageGrader.CACHE_KEYWORDS):
                feedback = (
                    "Alert acknowledged: cache-redis miss rate > 60%. "
                    "Cache miss rate elevated, possibly due to upstream DB issues."
                )
            elif matches_any(action.value, AlertTriageGrader.GATEWAY_KEYWORDS):
                feedback = (
                    "Alert acknowledged: api-gateway 503 rate increasing. "
                    "Gateway is returning 503s because upstream services are failing."
                )
            else:
                feedback = f"Alert acknowledgment noted for: {action.value}"

        elif action.action_type == "diagnose":
            feedback = f"Diagnosis recorded: {action.value[:200]}"

        elif action.action_type == "run_query":
            feedback = "No specific query system for this task. Use diagnose to share your analysis."

        elif action.action_type == "apply_fix":
            feedback = f"Fix action noted: {action.value[:200]}"

        elif action.action_type == "escalate":
            feedback = f"Escalation recorded: {action.value[:200]}"

        elif action.action_type == "write_postmortem":
            feedback = "Postmortem recorded. (Not required for this task but noted.)"

        elif action.action_type == "noop":
            feedback = "No action taken."

        obs = self.get_initial_observation()
        obs.current_step = self.current_step
        obs.time_elapsed_seconds = self.time_elapsed
        return obs, feedback
