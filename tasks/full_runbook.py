"""
Task 3: Full Incident Runbook (Hard) — max_steps=15
Three cascading failures: Redis OOM → auth cache storm → auth CPU spike →
mobile API circuit breaker → company-wide login outage.
Root cause: Redis maxmemory policy set to noeviction.
"""

from typing import Any, Dict, List, Tuple

from data.scenarios import (
    FULL_RUNBOOK_ALERTS,
    FULL_RUNBOOK_GOAL,
    FULL_RUNBOOK_HINT,
    FULL_RUNBOOK_LOGS,
    FULL_RUNBOOK_METRICS,
    FULL_RUNBOOK_QUERY_KEYWORDS,
    FULL_RUNBOOK_QUERY_RESULTS,
)
from graders.base_grader import BaseGrader, matches_any, matches_any_regex
from models import ActionModel, ObservationModel
from tasks.base_task import BaseTask


class FullRunbookGrader(BaseGrader):
    """
    Grader for the Full Incident Runbook task.

    Criteria (sum to 1.0):
    +0.10 → correct triage: identifies redis memory as P1 root cause
    +0.10 → correct triage: identifies auth-service as P1 secondary
    +0.15 → diagnoses redis OOM as the origin
    +0.15 → diagnoses cascade chain correctly
    +0.10 → applies correct fix 1: redis memory fix
    +0.10 → applies correct fix 2: restart/recover auth-service
    +0.10 → applies fixes in correct ORDER
    +0.10 → postmortem contains timeline section
    +0.10 → postmortem contains root cause analysis section
    """

    CRITERIA = {
        "triage_redis_p1": 0.10,
        "triage_auth_p1": 0.10,
        "diagnose_redis_oom": 0.15,
        "diagnose_cascade": 0.15,
        "fix_redis": 0.10,
        "fix_auth": 0.10,
        "fix_order_correct": 0.10,
        "postmortem_timeline": 0.10,
        "postmortem_root_cause": 0.10,
    }

    REDIS_KEYWORDS = [
        "redis", "cache", "redis memory", "oom", "out of memory",
        "maxmemory", "noeviction", "memory full", "redis oom",
        "redis_memory", "redis server",
    ]

    AUTH_KEYWORDS = [
        "auth", "auth-service", "auth_service", "authentication",
        "auth service", "session", "token validation",
    ]

    MOBILE_KEYWORDS = [
        "mobile", "mobile-api", "mobile_api", "mobile api",
        "circuit breaker", "circuit-breaker", "login",
    ]

    CASCADE_KEYWORDS = [
        "cascade", "cascading", "chain", "domino",
        "downstream", "propagat", "ripple",
    ]

    CASCADE_PATTERNS = [
        r"redis.*auth", r"cache.*auth", r"oom.*auth",
        r"redis.*mobile", r"auth.*mobile", r"auth.*circuit",
        r"memory.*cache.*auth", r"redis.*session",
        r"circuit.?breaker",
    ]

    REDIS_FIX_KEYWORDS = [
        "maxmemory", "eviction policy", "eviction", "allkeys-lru",
        "volatile-lru", "increase.*redis", "redis memory", "increase memory",
        "set maxmemory", "change policy", "redis config", "memory limit",
        "flush", "flushdb", "flushall", "clear redis", "free memory",
        "increase redis memory", "redis fix", "fix redis",
    ]

    AUTH_FIX_KEYWORDS = [
        "restart auth", "recover auth", "auth restart", "auth recover",
        "restart auth-service", "restart auth service", "bounce auth",
        "redeploy auth", "scale auth", "auth pods", "kill auth",
        "fix auth", "auth fix", "reset auth", "auth reset",
    ]

    TIMELINE_KEYWORDS = [
        "timeline", "chronolog", "sequence of events", "time of",
        "incident timeline", "event log", "02:00", "when",
        "started at", "began at", "first occurred",
    ]

    ROOT_CAUSE_ANALYSIS_KEYWORDS = [
        "root cause", "root_cause", "rca", "underlying cause",
        "primary cause", "origin", "fundamental issue",
        "because", "caused by", "due to", "reason",
    ]

    P1_KEYWORDS = [
        "p1", "priority 1", "critical", "sev1", "sev 1",
        "highest", "urgent", "root cause", "primary",
    ]

    def __init__(self) -> None:
        super().__init__(self.CRITERIA)
        self.fix_history: List[str] = []  # Track fix targets for order checking

    def evaluate_action(self, action_type: str, value: str, action_history: List[Tuple[str, str]]) -> str:
        """Evaluate an action against all grading criteria."""
        messages = []
        val_lower = value.lower()

        # ── Triage checks ──
        if action_type in ("acknowledge_alert", "diagnose"):
            # Redis as P1 root cause
            if matches_any(val_lower, self.REDIS_KEYWORDS) and matches_any(val_lower, self.P1_KEYWORDS):
                if self.award("triage_redis_p1"):
                    messages.append("Correctly triaged redis as P1 root cause")

            # Auth as P1 secondary
            if matches_any(val_lower, self.AUTH_KEYWORDS) and matches_any(val_lower, self.P1_KEYWORDS):
                if self.award("triage_auth_p1"):
                    messages.append("Correctly triaged auth-service as P1 secondary")

        # ── Diagnosis checks ──
        if action_type == "diagnose":
            # Redis OOM as origin
            if matches_any(val_lower, self.REDIS_KEYWORDS) and matches_any(val_lower, ["oom", "out of memory", "memory", "maxmemory", "noeviction"]):
                if self.award("diagnose_redis_oom"):
                    messages.append("Correctly diagnosed Redis OOM as the origin")

            # Cascade chain
            if matches_any(val_lower, self.CASCADE_KEYWORDS) or matches_any_regex(val_lower, self.CASCADE_PATTERNS):
                if self.award("diagnose_cascade"):
                    messages.append("Correctly diagnosed the cascade chain")

        # ── Fix checks ──
        if action_type == "apply_fix":
            # Redis fix
            if matches_any(val_lower, self.REDIS_KEYWORDS) or matches_any(val_lower, self.REDIS_FIX_KEYWORDS):
                if matches_any(val_lower, self.REDIS_FIX_KEYWORDS) or matches_any(val_lower, self.REDIS_KEYWORDS):
                    self.fix_history.append("redis")
                    if self.award("fix_redis"):
                        messages.append("Applied Redis memory fix")

            # Auth fix
            if matches_any(val_lower, self.AUTH_KEYWORDS) or matches_any(val_lower, self.AUTH_FIX_KEYWORDS):
                if matches_any(val_lower, self.AUTH_FIX_KEYWORDS) or matches_any(val_lower, self.AUTH_KEYWORDS):
                    self.fix_history.append("auth")
                    if self.award("fix_auth"):
                        messages.append("Applied auth-service recovery fix")

            # Mobile fix (for order tracking)
            if matches_any(val_lower, self.MOBILE_KEYWORDS):
                self.fix_history.append("mobile")

            # Check fix order after each fix
            self._check_fix_order()

        # ── Postmortem checks ──
        if action_type == "write_postmortem":
            if matches_any(val_lower, self.TIMELINE_KEYWORDS):
                if self.award("postmortem_timeline"):
                    messages.append("Postmortem contains timeline section")

            if matches_any(val_lower, self.ROOT_CAUSE_ANALYSIS_KEYWORDS):
                if self.award("postmortem_root_cause"):
                    messages.append("Postmortem contains root cause analysis")

            # Also check for other criteria in comprehensive postmortems
            if matches_any(val_lower, self.REDIS_KEYWORDS):
                self.award("diagnose_redis_oom")
                if matches_any(val_lower, self.P1_KEYWORDS):
                    self.award("triage_redis_p1")
            if matches_any(val_lower, self.CASCADE_KEYWORDS) or matches_any_regex(val_lower, self.CASCADE_PATTERNS):
                self.award("diagnose_cascade")

        # ── Comprehensive diagnose/postmortem: award any matching criteria ──
        if action_type in ("diagnose", "write_postmortem"):
            if matches_any(val_lower, self.REDIS_KEYWORDS) and matches_any(val_lower, self.P1_KEYWORDS):
                self.award("triage_redis_p1")
            if matches_any(val_lower, self.AUTH_KEYWORDS) and matches_any(val_lower, self.P1_KEYWORDS):
                self.award("triage_auth_p1")
            if matches_any(val_lower, self.REDIS_KEYWORDS) and matches_any(val_lower, ["oom", "out of memory", "memory", "maxmemory", "noeviction"]):
                self.award("diagnose_redis_oom")
            if matches_any(val_lower, self.CASCADE_KEYWORDS) or matches_any_regex(val_lower, self.CASCADE_PATTERNS):
                self.award("diagnose_cascade")

        # Penalty: apply_fix on wrong service when root cause not identified
        if action_type == "apply_fix":
            root_cause_found = "diagnose_redis_oom" in self.scored_criteria
            if not root_cause_found:
                if not matches_any(val_lower, self.REDIS_KEYWORDS) and not matches_any(val_lower, self.REDIS_FIX_KEYWORDS):
                    self.apply_penalty(0.05, "Applied fix before identifying root cause")

        return " | ".join(messages) if messages else "Action noted."

    def _check_fix_order(self) -> None:
        """
        Check if fixes were applied in the correct order:
        1. Redis first
        2. Auth second
        3. Mobile third (optional)
        """
        if len(self.fix_history) < 2:
            return

        # Find first occurrence of each service in fix history
        redis_idx = None
        auth_idx = None
        mobile_idx = None

        for i, target in enumerate(self.fix_history):
            if target == "redis" and redis_idx is None:
                redis_idx = i
            elif target == "auth" and auth_idx is None:
                auth_idx = i
            elif target == "mobile" and mobile_idx is None:
                mobile_idx = i

        order_correct = True

        # Redis must come before auth
        if redis_idx is not None and auth_idx is not None:
            if redis_idx > auth_idx:
                order_correct = False

        # Auth must come before mobile
        if auth_idx is not None and mobile_idx is not None:
            if auth_idx > mobile_idx:
                order_correct = False

        # Redis must come before mobile
        if redis_idx is not None and mobile_idx is not None:
            if redis_idx > mobile_idx:
                order_correct = False

        if order_correct and redis_idx is not None and auth_idx is not None:
            self.award("fix_order_correct")


class FullIncidentRunbookTask(BaseTask):
    """Task 3: Full Incident Runbook — Hard difficulty."""

    @property
    def task_id(self) -> str:
        return "full_incident_runbook"

    @property
    def task_name(self) -> str:
        return "Full Incident Runbook"

    @property
    def difficulty(self) -> str:
        return "hard"

    @property
    def max_steps(self) -> int:
        return 15

    @property
    def scenario_name(self) -> str:
        return "Full Incident Runbook — Redis OOM Cascade to Login Outage"

    def create_grader(self) -> BaseGrader:
        return FullRunbookGrader()

    def get_initial_observation(self) -> ObservationModel:
        return ObservationModel(
            logs=FULL_RUNBOOK_LOGS,
            metrics=FULL_RUNBOOK_METRICS,
            active_alerts=FULL_RUNBOOK_ALERTS,
            task_goal=FULL_RUNBOOK_GOAL,
            current_step=self.current_step,
            max_steps=self.max_steps,
            time_elapsed_seconds=self.time_elapsed,
            available_actions=self.get_available_actions(),
            hint=FULL_RUNBOOK_HINT,
        )

    def _resolve_query(self, query_value: str) -> List[str]:
        """
        Resolve a run_query action to appropriate log results.
        Uses fuzzy keyword matching against the query value.
        """
        query_lower = query_value.lower()

        for result_key, keywords in FULL_RUNBOOK_QUERY_KEYWORDS.items():
            if matches_any(query_lower, keywords):
                return FULL_RUNBOOK_QUERY_RESULTS[result_key]

        return [
            f"No results found for query: '{query_value}'.",
            "Try querying: redis, auth, mobile, circuit breaker, memory",
        ]

    def process_action(self, action: ActionModel) -> Tuple[ObservationModel, str]:
        """Process an action and return updated observation with feedback."""
        feedback = ""
        obs = self.get_initial_observation()

        if action.action_type == "acknowledge_alert":
            if matches_any(action.value, FullRunbookGrader.REDIS_KEYWORDS):
                feedback = (
                    "Alert acknowledged: Redis memory > 99%. "
                    "Redis is OOM with noeviction policy — all writes are being rejected. "
                    "This is likely the root cause of the cascade."
                )
            elif matches_any(action.value, FullRunbookGrader.AUTH_KEYWORDS):
                feedback = (
                    "Alert acknowledged: auth-service CPU > 90%. "
                    "Auth service is in a retry storm due to failed cache writes. "
                    "DB fallback is also saturated."
                )
            elif matches_any(action.value, FullRunbookGrader.MOBILE_KEYWORDS):
                feedback = (
                    "Alert acknowledged: mobile-api circuit breaker OPEN. "
                    "All login requests are failing. 47,000 users affected."
                )
            else:
                feedback = f"Alert acknowledgment noted for: {action.value}"

        elif action.action_type == "run_query":
            query_results = self._resolve_query(action.value)
            obs.logs = query_results
            feedback = f"Query executed: {action.value}. Results returned in logs."

        elif action.action_type == "diagnose":
            feedback = f"Diagnosis recorded: {action.value[:300]}"

        elif action.action_type == "apply_fix":
            if matches_any(action.value, FullRunbookGrader.REDIS_FIX_KEYWORDS) or (
                matches_any(action.value, FullRunbookGrader.REDIS_KEYWORDS) and matches_any(action.value, ["fix", "config", "set", "change", "update", "increase", "flush"])
            ):
                feedback = (
                    "Redis fix applied. Changed maxmemory-policy from noeviction to allkeys-lru. "
                    "Increased maxmemory to 8GB. Redis is now evicting old keys and accepting writes. "
                    "Memory usage dropping."
                )
                obs.metrics = dict(FULL_RUNBOOK_METRICS)
                obs.metrics["redis_memory_usage_percent"] = 72.0
                obs.metrics["redis_rejected_commands"] = 0.0
            elif matches_any(action.value, FullRunbookGrader.AUTH_FIX_KEYWORDS) or (
                matches_any(action.value, FullRunbookGrader.AUTH_KEYWORDS) and matches_any(action.value, ["fix", "restart", "recover", "reset", "bounce"])
            ):
                feedback = (
                    "Auth-service fix applied. Restarted auth-service pods. "
                    "Retry storm halted. Cache writes succeeding now that Redis is healthy. "
                    "CPU dropping to normal levels."
                )
                obs.metrics = dict(FULL_RUNBOOK_METRICS)
                obs.metrics["auth_cpu_percent"] = 35.0
                obs.metrics["auth_cache_hit_rate"] = 78.0
                obs.metrics["auth_db_connections"] = 45.0
            elif matches_any(action.value, FullRunbookGrader.MOBILE_KEYWORDS) or matches_any(action.value, ["circuit breaker", "circuit-breaker"]):
                feedback = (
                    "Mobile-api fix applied. Circuit breaker manually reset. "
                    "Login requests are now reaching auth-service successfully. "
                    "Login success rate recovering."
                )
                obs.metrics = dict(FULL_RUNBOOK_METRICS)
                obs.metrics["mobile_api_error_rate"] = 5.0
                obs.metrics["mobile_login_success_rate"] = 92.0
                obs.metrics["circuit_breaker_status"] = 0.0
            else:
                feedback = f"Fix action noted: {action.value[:200]}"

        elif action.action_type == "escalate":
            feedback = f"Escalation recorded: {action.value[:200]}"

        elif action.action_type == "write_postmortem":
            feedback = "Postmortem recorded and stored in incident management system."

        elif action.action_type == "noop":
            feedback = "No action taken. This is a SEV1 incident — 47,000 users cannot log in."

        obs.current_step = self.current_step
        obs.time_elapsed_seconds = self.time_elapsed
        return obs, feedback
