# IMPROVED: Harder grading, red herrings, strict fix order, complete postmortem required

from typing import Any, Dict, List, Tuple
from graders.base_grader import BaseGrader, matches_any, matches_any_regex
from models import ActionModel, ObservationModel

# Instead of importing static scenarios directly, we defer to dynamic variants in get_initial_observation

class FullRunbookGrader(BaseGrader):
    """
    Grader for the Full Incident Runbook task.
    """
    CRITERIA = {
        "triage_redis_p1": 0.08,
        "triage_auth_p1": 0.08,
        "diagnose_redis_oom": 0.12,
        "diagnose_cascade_chain": 0.12,
        "apply_redis_fix": 0.10,
        "apply_auth_fix": 0.08,
        "apply_mobile_fix": 0.07,
        "fix_correct_order": 0.10,
        "postmortem_timeline": 0.05,
        "postmortem_rca": 0.05,
        "postmortem_actions": 0.05,
        "postmortem_prevention": 0.05,
        "no_wrong_service_blame": 0.05,
    }

    REDIS_KEYWORDS = ["redis", "cache", "redis memory", "oom", "out of memory", "maxmemory", "noeviction", "redis oom", "redis server", "memory limit", "eviction"]
    AUTH_KEYWORDS = ["auth", "auth-service", "auth_service", "authentication", "auth service", "session"]
    MOBILE_KEYWORDS = ["mobile", "mobile-api", "mobile_api", "mobile api", "circuit breaker", "circuit-breaker", "login"]
    CASCADE_KEYWORDS = ["cascade", "chain", "domino", "downstream", "propagat", "ripple"]
    CASCADE_PATTERNS = [r"redis.*auth", r"redis.*mobile", r"auth.*mobile", r"circuit.?breaker", r"auth.*circuit"]

    # STOLEN FROM PROMPT (D: Require More Specific Fix Values)
    REDIS_FIX_KEYWORDS = [
        "maxmemory-policy", "allkeys-lru", "allkeys-lfu", "noeviction", 
        "redis maxmemory", "eviction policy", "increase redis memory",
        "redis memory limit", "config set maxmemory", "set maxmemory-policy"
    ]
    AUTH_FIX_KEYWORDS = ["restart auth", "recover auth", "auth restart", "auth recover", "bounce auth", "reset auth"]
    
    TIMELINE_KEYWORDS = ["timeline", "chronolog"]
    RCA_KEYWORDS = ["root cause", "rca"]
    ACTION_KEYWORDS = ["action items", "follow-up", "remediation", "action item"]
    PREVENTION_KEYWORDS = ["prevention", "prevent", "avoid", "mitigation"]
    
    P1_KEYWORDS = ["p1", "priority 1", "critical", "sev1", "sev 1", "highest", "root cause"]

    def __init__(self) -> None:
        super().__init__(self.CRITERIA)
        self.fix_history: List[str] = []
        self.award("no_wrong_service_blame")

    def evaluate_action(self, action_type: str, value: str, action_history: List[Tuple[str, str]]) -> str:
        messages = []
        val_lower = value.lower()

        # Wrong service blame penalty
        if "diagnose_redis_oom" not in self.scored_criteria:
            if action_type == "apply_fix":
                if any(w in val_lower for w in ["api-gateway", "payment", "gateway", "memory leak"]):
                    self.apply_penalty(0.10, "Applied fix to wrong service before root cause identified")
            if action_type == "diagnose":
                if ("api-gateway" in val_lower or "payment-service" in val_lower) and "redis" not in val_lower and "auth" not in val_lower:
                    self.apply_penalty(0.05, "Blamed wrong service")
                    if "no_wrong_service_blame" in self.scored_criteria:
                        self.scored_criteria.remove("no_wrong_service_blame")
                        self.scores["no_wrong_service_blame"] = 0.0
                        self.info = [{"penalty": "Applied fix to wrong service before root cause identified"}]

        # Triage checks
        if action_type in ("acknowledge_alert", "diagnose"):
            if matches_any(val_lower, self.REDIS_KEYWORDS) and matches_any(val_lower, self.P1_KEYWORDS):
                if self.award("triage_redis_p1"): messages.append("Triaged redis P1")
            if matches_any(val_lower, self.AUTH_KEYWORDS) and matches_any(val_lower, self.P1_KEYWORDS):
                if self.award("triage_auth_p1"): messages.append("Triaged auth P1")

        # Diagnosis
        if action_type == "diagnose":
            if matches_any(val_lower, self.REDIS_KEYWORDS) and matches_any(val_lower, ["oom", "out of memory", "maxmemory"]):
                if self.award("diagnose_redis_oom"): messages.append("Diagnosed Redis OOM")
            if matches_any(val_lower, self.CASCADE_KEYWORDS) or matches_any_regex(val_lower, self.CASCADE_PATTERNS):
                if self.award("diagnose_cascade_chain"): messages.append("Diagnosed cascade")

        # Fixes
        if action_type == "apply_fix":
            if matches_any(val_lower, self.REDIS_FIX_KEYWORDS):
                self.fix_history.append("redis")
                if self.award("apply_redis_fix"): messages.append("Redis fix applied")
            elif matches_any(val_lower, self.AUTH_KEYWORDS) or matches_any(val_lower, self.AUTH_FIX_KEYWORDS):
                self.fix_history.append("auth")
                if self.award("apply_auth_fix"): messages.append("Auth fix applied")
            elif matches_any(val_lower, self.MOBILE_KEYWORDS):
                self.fix_history.append("mobile")
                if self.award("apply_mobile_fix"): messages.append("Mobile fix applied")
            self._check_fix_order()

        # Postmortem
        if action_type == "write_postmortem":
            if matches_any(val_lower, self.TIMELINE_KEYWORDS): self.award("postmortem_timeline")
            if matches_any(val_lower, self.RCA_KEYWORDS): self.award("postmortem_rca")
            if matches_any(val_lower, self.ACTION_KEYWORDS): self.award("postmortem_actions")
            if matches_any(val_lower, self.PREVENTION_KEYWORDS): self.award("postmortem_prevention")

        # Fallback comprehensive checks
        if action_type in ("diagnose", "write_postmortem"):
            if matches_any(val_lower, self.REDIS_KEYWORDS) and matches_any(val_lower, ["oom", "maxmemory-policy"]):
                self.award("diagnose_redis_oom")
            if matches_any(val_lower, self.CASCADE_PATTERNS):
                self.award("diagnose_cascade_chain")

        return " | ".join(messages) if messages else "Action noted."

    def _check_fix_order(self) -> None:
        if len(self.fix_history) >= 2:
            try:
                r = self.fix_history.index("redis")
                a = self.fix_history.index("auth")
                m = self.fix_history.index("mobile") if "mobile" in self.fix_history else 99
                if r < a and a < m:
                    self.award("fix_correct_order")
            except ValueError:
                pass

        
from tasks.base_task import BaseTask

class FullIncidentRunbookTask(BaseTask):
    @property
    def task_id(self) -> str: return "full_incident_runbook"

    @property
    def task_name(self) -> str: return "Full Incident Runbook"

    @property
    def difficulty(self) -> str: return "hard"

    @property
    def max_steps(self) -> int: return 20

    @property
    def scenario_name(self) -> str: return getattr(self, "scenario_variant", {}).get("name", "Full Incident Runbook — Redis OOM Cascade to Login Outage")

    def create_grader(self) -> BaseGrader:
        return FullRunbookGrader()

    def get_initial_observation(self) -> ObservationModel:
        v = getattr(self, "scenario_variant", None)
        if v:
            logs = list(v["logs"])
            metrics = dict(v["metrics"])
            alerts = list(v["alerts"])
            goal = v["goal"]
            hint = v["hint"]
        else:
            # Fallback for old behaviour 
            from data.scenarios import FULL_RUNBOOK_LOGS, FULL_RUNBOOK_METRICS, FULL_RUNBOOK_ALERTS, FULL_RUNBOOK_GOAL, FULL_RUNBOOK_HINT
            logs = list(FULL_RUNBOOK_LOGS)
            metrics = dict(FULL_RUNBOOK_METRICS)
            alerts = list(FULL_RUNBOOK_ALERTS)
            goal = FULL_RUNBOOK_GOAL
            hint = FULL_RUNBOOK_HINT

        # Add red herrings for base scenario (if redis keywords exist)
        if any("redis" in str(x).lower() for x in alerts):
            alerts.extend([
                "WARNING: api-gateway connection pool at 75% — may be contributing to failures",
                "INFO: payment-service heap memory at 78% — possible memory leak",
                "WARNING: db-primary replication lag 2.3s — replica falling behind"
            ])
            metrics["api_gateway_pool_usage"] = 75.0
            metrics["payment_heap_percent"] = 78.0

        return ObservationModel(
            logs=logs,
            metrics=metrics,
            active_alerts=alerts,
            task_goal=goal,
            current_step=self.current_step,
            max_steps=self.max_steps,
            time_elapsed_seconds=self.time_elapsed,
            available_actions=self.get_available_actions(),
            hint=hint,
            session_id=None
        )

    def step(self, action: ActionModel) -> Dict[str, Any]:
        if not hasattr(self, "VALID_ACTION_TYPES"):
            self.VALID_ACTION_TYPES = {
                "acknowledge_alert", "diagnose", "run_query",
                "apply_fix", "escalate", "write_postmortem", "noop"
            }
        
        if getattr(self, "_peak_reward", None) is None:
            self._peak_reward = 0.0

        if getattr(self, "grader", None) is None:
            self.grader = self.create_grader()

        # ── NOOP HANDLER — must never throw exception ──────────
        if action.action_type not in self.VALID_ACTION_TYPES or action.action_type == "noop":
            self.current_step += 1
            noop_penalty = 0.02 if self.current_step > 5 else 0.0
            
            effective_reward = max(0.0, self.grader.total_reward - noop_penalty)
            done = self.current_step >= self.max_steps or effective_reward >= 0.95
            self.done = done
            
            grade_msg = "No action taken." if action.action_type == "noop" else f"Invalid action type: {action.action_type}"
            
            obs = self.get_initial_observation()
            obs.current_step = self.current_step
            obs.time_elapsed_seconds = self.time_elapsed
            
            return {
                "observation": obs,
                "reward": effective_reward,
                "done": done,
                "success": self._peak_reward >= 0.5,
                "info": {
                    "step": self.current_step,
                    "action_type": action.action_type,
                    "action_value": action.value,
                    "grade_message": grade_msg,
                    "grader_breakdown": self.grader.breakdown,
                    "reward_detail": {
                        "total": effective_reward,
                        "breakdown": self.grader.breakdown,
                        "message": f"Step {self.current_step}: noop/invalid action"
                    },
                    "error": None
                }
            }
        # ── END NOOP HANDLER ───────────────────────────────────

        try:
            result = super().step(action)
            if result["reward"] > self._peak_reward:
                self._peak_reward = result["reward"]
            result["success"] = self._peak_reward >= 0.5
            return result
        except Exception as e:
            self.current_step += 1
            done = self.current_step >= self.max_steps
            self.done = done
            
            obs = self.get_initial_observation()
            obs.current_step = self.current_step
            obs.time_elapsed_seconds = self.time_elapsed
            
            return {
                "observation": obs,
                "reward": self.grader.total_reward,
                "done": done,
                "success": self._peak_reward >= 0.5,
                "info": {
                    "step": self.current_step,
                    "action_type": action.action_type,
                    "action_value": action.value,
                    "grade_message": "Grader error — action recorded",
                    "grader_breakdown": self.grader.breakdown,
                    "reward_detail": {
                        "total": self.grader.total_reward,
                        "breakdown": self.grader.breakdown,
                        "message": f"Error: {str(e)}"
                    },
                    "error": None
                }
            }

    def process_action(self, action: ActionModel) -> Tuple[ObservationModel, str]:
        obs = self.get_initial_observation()
        feedback = f"Action noted: {action.value[:100]}"
        
        # Implement some basic feedback for fix actions
        if action.action_type == "apply_fix":
            obs.metrics["redis_memory_usage_percent"] = 72.0
            
        obs.current_step = self.current_step
        obs.time_elapsed_seconds = self.time_elapsed
        return obs, feedback

# Apply Metaprogramming to monkeypatch BaseTask.reset globally
def _apply_dynamic_variants():
    import random
    from data.scenarios import TASK_SCENARIOS
    from tasks.base_task import BaseTask
    from tasks.alert_triage import AlertTriageTask
    from tasks.root_cause import RootCauseDiagnosisTask

    orig_reset = BaseTask.reset
    def newly_patched_reset(self):
        scenario = random.choice(TASK_SCENARIOS[self.task_id])
        self.scenario_variant = scenario
        obs = orig_reset(self)
        if hasattr(self, 'scenario_variant') and 'grader_keywords' in self.scenario_variant:
            # Override instance attributes natively
            for attr, val in self.scenario_variant['grader_keywords'].items():
                setattr(self.grader, attr, val)
        return obs
    BaseTask.reset = newly_patched_reset

    orig_step = BaseTask.step
    def newly_patched_step(self, action):
        res = orig_step(self, action)
        if hasattr(self, 'scenario_variant'):
            res['info']['scenario_variant'] = self.scenario_variant['name']
        return res
    BaseTask.step = newly_patched_step

    def patch_get_obs(task_cls):
        orig_get_obs = task_cls.get_initial_observation
        def new_get_obs(self):
            obs = orig_get_obs(self)
            if hasattr(self, 'scenario_variant'):
                v = self.scenario_variant
                obs.logs = list(v['logs'])
                obs.metrics = dict(v['metrics'])
                obs.active_alerts = list(v['alerts'])
                obs.task_goal = v['goal']
                if 'hint' in v:
                    obs.hint = v['hint']
            return obs
        task_cls.get_initial_observation = new_get_obs

    patch_get_obs(AlertTriageTask)
    patch_get_obs(RootCauseDiagnosisTask)

_apply_dynamic_variants()
