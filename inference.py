"""
Baseline inference agent for the SRE Incident Response OpenEnv environment.
Uses the OpenAI client to interact with an LLM and solve all 3 tasks.

Must be in the root directory of the project.
Must use OpenAI client ONLY (no other LLM libraries).
Runtime must be under 20 minutes on 2 vCPU, 8GB RAM.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ═══════════════════════════════════════════════════════════
# Environment Variables
# ═══════════════════════════════════════════════════════════

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")

# ═══════════════════════════════════════════════════════════
# OpenAI Client
# ═══════════════════════════════════════════════════════════

if not API_KEY:
    print("WARNING: No API key found. Set API_KEY, HF_TOKEN or OPENAI_API_KEY environment variable.")
    print("Falling back to dummy mode — actions will be hardcoded.")

client: Optional[OpenAI] = None
if API_KEY:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# ═══════════════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert SRE engineer responding to a production incident.
You will receive logs, metrics, and alerts. You must take actions to 
triage, diagnose, and resolve the incident.
Available action types: acknowledge_alert, diagnose, run_query, apply_fix, 
escalate, write_postmortem, noop.
Respond with ONLY a JSON object like:
{"action_type": "diagnose", "value": "your diagnosis here"}
No explanation. No markdown. Just the JSON object."""

# ═══════════════════════════════════════════════════════════
# All 3 task IDs
# ═══════════════════════════════════════════════════════════

TASK_IDS = ["alert_triage", "root_cause_diagnosis", "full_incident_runbook"]

# ═══════════════════════════════════════════════════════════
# Hardcoded fallback actions (used when no LLM key is available)
# ═══════════════════════════════════════════════════════════

FALLBACK_ACTIONS: Dict[str, List[Dict[str, str]]] = {
    "alert_triage": [
        {"action_type": "acknowledge_alert", "value": "CRITICAL: db-primary CPU > 95% — this is the P1 root cause alert. Database CPU at 98% is causing cascading failures to all downstream services."},
        {"action_type": "diagnose", "value": "Root cause: db-primary CPU overload at 98%. This is causing a cascading failure chain. The db-primary CPU is the P1 root cause. payment-service is P1 critical due to direct dependency on db-primary. auth-service is P2 warning — elevated latency is a symptom. cache-redis is P2 warning — elevated miss rate is a downstream symptom. api-gateway is P3 info — 503s are a downstream symptom of payment-service failures. The cascade chain: db CPU overload → connection queue backup → payment-service connection timeouts → API gateway 503s. Cache and auth degradation are secondary symptoms propagating from the database overload."},
        {"action_type": "acknowledge_alert", "value": "CRITICAL: payment-service error rate > 30% — P1 critical, direct victim of db-primary CPU overload"},
        {"action_type": "acknowledge_alert", "value": "WARNING: auth-service p99 latency > 800ms — P2 warning, symptom of db overload"},
        {"action_type": "acknowledge_alert", "value": "WARNING: cache-redis miss rate > 60% — P2 warning, symptom of upstream db issues"},
        {"action_type": "acknowledge_alert", "value": "INFO: api-gateway 503 rate increasing — P3 informational, downstream symptom"},
    ],
    "root_cause_diagnosis": [
        {"action_type": "acknowledge_alert", "value": "CRITICAL: payment-service HTTP 503 — acknowledging the primary incident alert"},
        {"action_type": "run_query", "value": "slow queries"},
        {"action_type": "run_query", "value": "recent deploy history"},
        {"action_type": "run_query", "value": "connection pool status"},
        {"action_type": "diagnose", "value": "Root cause identified: Deploy v2.4.1 introduced a slow SQL query (SELECT * FROM orders JOIN customers... taking 47.3s). This slow query exhausted the DB connection pool (490/500 connections, 847 queries in queue). With the pool exhausted, payment-service cannot acquire DB connections and returns HTTP 503. The fix is to rollback to v2.4.0 to eliminate the slow query and restore connection pool health."},
        {"action_type": "apply_fix", "value": "Rollback payment-service from v2.4.1 to v2.4.0. This will remove the slow query introduced in the bad deploy and allow the connection pool to recover."},
    ],
    "full_incident_runbook": [
        {"action_type": "acknowledge_alert", "value": "CRITICAL: redis memory > 99% — P1 root cause. Redis OOM with noeviction policy is the origin of the cascade."},
        {"action_type": "acknowledge_alert", "value": "CRITICAL: auth-service CPU > 90% — P1 secondary. Auth retry storm caused by Redis OOM."},
        {"action_type": "run_query", "value": "redis memory breakdown"},
        {"action_type": "run_query", "value": "auth service errors"},
        {"action_type": "diagnose", "value": "Root cause: Redis OOM with maxmemory policy set to noeviction. The cascade chain: Redis memory filled to 99.8% (3.99GB/4GB) → Redis rejected all write commands → auth-service cache writes failed → auth-service entered retry storm (CPU 94%) → auth-service DB fallback also saturated → auth-service returning 503 → mobile-api circuit breaker opened → 100% login failure company-wide. This is a cascading failure originating from Redis infrastructure."},
        {"action_type": "apply_fix", "value": "Fix Redis: Change maxmemory-policy from noeviction to allkeys-lru. Increase maxmemory from 4GB to 8GB. This will allow Redis to evict old keys and accept new writes."},
        {"action_type": "apply_fix", "value": "Fix auth-service: Restart auth-service pods to clear the retry storm. With Redis now healthy, cache operations will succeed and CPU will normalize."},
        {"action_type": "apply_fix", "value": "Fix mobile-api: Reset circuit breaker for auth-service. With auth-service now healthy, login requests will succeed."},
        {"action_type": "write_postmortem", "value": "# Incident Postmortem: Company-Wide Login Outage\n\n## Timeline\n- 02:00:01 UTC: Redis hit maxmemory limit (4GB) with noeviction policy\n- 02:00:10 UTC: Auth-service cache writes began failing with OOM errors\n- 02:00:25 UTC: Auth-service CPU spiked to 94% from retry storm\n- 02:00:40 UTC: Mobile-api auth validation requests started failing\n- 02:00:48 UTC: Mobile-api circuit breaker OPENED for auth-service\n- 02:00:50 UTC: 100% of login requests failing company-wide\n- 02:01:00 UTC: SEV1 incident declared, 47,000 users affected\n\n## Root Cause Analysis\nThe root cause was Redis maxmemory-policy set to 'noeviction'. When Redis memory reached its 4GB limit, it began rejecting all write commands instead of evicting old keys. This caused auth-service session cache writes to fail, triggering a retry storm that spiked CPU and exhausted DB fallback connections. The auth-service failure propagated to mobile-api, which opened its circuit breaker, causing complete login failure.\n\n## Action Items\n1. Change Redis maxmemory-policy to allkeys-lru in all environments\n2. Increase Redis maxmemory to 8GB\n3. Add Redis memory usage alerting at 80% threshold\n4. Implement auth-service circuit breaker for Redis writes\n5. Add session token TTL enforcement to prevent unbounded memory growth\n6. Implement graceful degradation in auth-service when cache is unavailable"},
    ],
}


def build_user_prompt(observation: Dict[str, Any]) -> str:
    """Build a user prompt from the observation data."""
    logs = observation.get("logs", [])
    metrics = observation.get("metrics", {})
    alerts = observation.get("active_alerts", [])
    goal = observation.get("task_goal", "")
    step = observation.get("current_step", 0)
    max_steps = observation.get("max_steps", 10)
    hint = observation.get("hint", "")

    prompt_parts = [
        f"INCIDENT STATUS — Step {step}/{max_steps}",
        f"\nGOAL: {goal}",
        "\n--- ACTIVE ALERTS ---",
    ]

    for i, alert in enumerate(alerts, 1):
        prompt_parts.append(f"{i}. {alert}")

    prompt_parts.append("\n--- RECENT LOGS ---")
    for log in logs[-10:]:
        prompt_parts.append(log)

    prompt_parts.append("\n--- METRICS ---")
    for key, val in metrics.items():
        prompt_parts.append(f"  {key}: {val}")

    if hint:
        prompt_parts.append(f"\nHINT: {hint}")

    prompt_parts.append(
        "\nRespond with ONLY a JSON object: {\"action_type\": \"...\", \"value\": \"...\"}"
    )

    return "\n".join(prompt_parts)


def get_llm_action(observation: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Call the LLM to get the next action.
    Falls back to hardcoded actions if no API key is set.
    """
    if client is None:
        return {"action_type": "noop", "value": "No LLM client available"}

    user_prompt = build_user_prompt(observation)
    conversation_history.append({"role": "user", "content": user_prompt})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history,
            ],
            temperature=0.2,
            max_tokens=1024,
        )

        content = response.choices[0].message.content or ""
        conversation_history.append({"role": "assistant", "content": content})

        # Parse JSON from response
        content = content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        action = json.loads(content)
        return {
            "action_type": action.get("action_type", "noop"),
            "value": action.get("value", ""),
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {"action_type": "noop", "value": f"Failed to parse LLM response: {e}"}
    except Exception as e:
        return {"action_type": "noop", "value": f"LLM call failed: {e}"}


def run_task(task_id: str) -> Dict[str, Any]:
    """
    Run a single task from start to finish.

    Returns dict with: task_id, steps, final_reward, success, rewards_per_step
    """
    use_fallback = client is None
    fallback_actions = FALLBACK_ACTIONS.get(task_id, [])
    fallback_idx = 0

    print(f"[START] task={task_id} env=sre-incident-response model={MODEL_NAME}")

    # Reset the environment
    try:
        resp = requests.post(
            f"{ENV_BASE_URL}/reset",
            json={"task_id": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        observation = resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to reset environment: {e}")
        return {
            "task_id": task_id,
            "steps": 0,
            "final_reward": 0.0,
            "success": False,
            "rewards_per_step": [],
        }

    done = False
    step_count = 0
    rewards: List[float] = []
    final_reward = 0.0
    success = False
    conversation_history: List[Dict[str, str]] = []

    while not done:
        # Get action from LLM or fallback
        if use_fallback and fallback_idx < len(fallback_actions):
            action = fallback_actions[fallback_idx]
            fallback_idx += 1
        elif use_fallback:
            action = {"action_type": "noop", "value": "No more fallback actions"}
        else:
            action = get_llm_action(observation, conversation_history)

        # Take a step
        try:
            resp = requests.post(
                f"{ENV_BASE_URL}/step",
                json=action,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            print(f"[ERROR] Step failed: {e}")
            break

        step_count += 1
        reward = result.get("reward", 0.0)
        done = result.get("done", False)
        success = result.get("success", False)
        observation = result.get("observation", {})
        info = result.get("info", {})
        error = info.get("error", None)

        rewards.append(reward)
        final_reward = reward

        # Truncate value for display
        display_value = action["value"][:80].replace("\n", " ")
        print(
            f"[STEP]  step={step_count} "
            f"action={action['action_type']}('{display_value}') "
            f"reward={reward:.2f} done={str(done).lower()} "
            f"error={error if error else 'null'}"
        )

    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END]   success={str(success).lower()} "
        f"steps={step_count} rewards={rewards_str}"
    )

    return {
        "task_id": task_id,
        "steps": step_count,
        "final_reward": final_reward,
        "success": success,
        "rewards_per_step": rewards,
    }


def main() -> None:
    """Run all 3 tasks sequentially and print a summary table."""
    print("=" * 60)
    print("SRE Incident Response — Baseline Inference Agent")
    print(f"Model: {MODEL_NAME}")
    print(f"API Base: {API_BASE_URL}")
    print(f"Environment: {ENV_BASE_URL}")
    print(f"API Key: {'set' if API_KEY else 'NOT SET (using fallback)'}")
    print("=" * 60)
    print()

    results: List[Dict[str, Any]] = []

    for task_id in TASK_IDS:
        result = run_task(task_id)
        results.append(result)
        print()

    # Print summary table
    print("BASELINE RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Task':<25} | {'Steps':>5} | {'Final Reward':>12} | {'Success':>7}")
    print("-" * 60)

    total_reward = 0.0
    for r in results:
        task_display = r["task_id"]
        steps = r["steps"]
        reward = r["final_reward"]
        success_str = str(r["success"]).lower()
        total_reward += reward
        print(f"{task_display:<25} | {steps:>5} | {reward:>12.2f} | {success_str:>7}")

    avg_reward = total_reward / len(results) if results else 0.0
    print("=" * 60)
    print(f"Average Score: {avg_reward:.2f}")
    print()


if __name__ == "__main__":
    main()
