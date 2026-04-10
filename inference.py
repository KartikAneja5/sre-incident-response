"""
Baseline inference agent for the SRE Incident Response OpenEnv environment.
Uses the OpenAI client to interact with an LLM and solve all 3 tasks.

Must be in the root directory of the project.
Must use OpenAI client ONLY (no other LLM libraries).
Runtime must be under 20 minutes on 2 vCPU, 8GB RAM.

STDOUT FORMAT:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI

# ═══════════════════════════════════════════════════════════
# Environment Variables — match exactly what validator injects
# ═══════════════════════════════════════════════════════════

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME   = os.getenv("MODEL_NAME")   or "Qwen/Qwen2.5-72B-Instruct"
API_KEY      = os.getenv("HF_TOKEN")     or os.getenv("API_KEY")
ENV_BASE_URL = os.getenv("ENV_BASE_URL") or "http://localhost:8000"

# ═══════════════════════════════════════════════════════════
# OpenAI Client — initialized exactly per reference script
# ═══════════════════════════════════════════════════════════

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

TASK_IDS = ["alert_triage", "root_cause_diagnosis", "full_incident_runbook"]
ENV_NAME = "sre-incident-response"

SYSTEM_PROMPT = """You are an expert SRE engineer responding to a production incident.
You will receive logs, metrics, and alerts. You must take actions to
triage, diagnose, and resolve the incident.
Available action types: acknowledge_alert, diagnose, run_query, apply_fix,
escalate, write_postmortem, noop.
Respond with ONLY a JSON object like:
{"action_type": "diagnose", "value": "your diagnosis here"}
No explanation. No markdown. Just the JSON object."""

# ═══════════════════════════════════════════════════════════
# Logging — flush=True required by validator
# ═══════════════════════════════════════════════════════════

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action_type: str, value: str, reward: float, done: bool, error: Optional[str]) -> None:
    display_value = value[:80].replace("\n", " ").replace("'", "")
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP]  step={step} "
        f"action={action_type}('{display_value}') "
        f"reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END]   success={str(success).lower()} "
        f"steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )

# ═══════════════════════════════════════════════════════════
# Prompt Builder
# ═══════════════════════════════════════════════════════════

def build_user_prompt(observation: Dict[str, Any]) -> str:
    logs        = observation.get("logs", [])
    metrics     = observation.get("metrics", {})
    alerts      = observation.get("active_alerts", [])
    goal        = observation.get("task_goal", "")
    step        = observation.get("current_step", 0)
    max_steps   = observation.get("max_steps", 10)
    hint        = observation.get("hint", "")

    parts = [
        f"INCIDENT STATUS — Step {step}/{max_steps}",
        f"\nGOAL: {goal}",
        "\n--- ACTIVE ALERTS ---",
    ]
    for i, alert in enumerate(alerts, 1):
        parts.append(f"{i}. {alert}")

    parts.append("\n--- RECENT LOGS ---")
    for log in logs[-10:]:
        parts.append(log)

    parts.append("\n--- METRICS ---")
    for key, val in metrics.items():
        parts.append(f"  {key}: {val}")

    if hint:
        parts.append(f"\nHINT: {hint}")

    parts.append(
        '\nRespond with ONLY a JSON object: {"action_type": "...", "value": "..."}'
    )

    return "\n".join(parts)

# ═══════════════════════════════════════════════════════════
# LLM Action
# ═══════════════════════════════════════════════════════════

def get_llm_action(
    observation: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
) -> Dict[str, str]:

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

        content = (response.choices[0].message.content or "").strip()
        conversation_history.append({"role": "assistant", "content": content})

        # Strip markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        action = json.loads(content)
        return {
            "action_type": str(action.get("action_type", "noop")),
            "value":       str(action.get("value", "")),
        }

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {"action_type": "noop", "value": f"Failed to parse LLM response: {e}"}
    except Exception as e:
        return {"action_type": "noop", "value": f"LLM call failed: {e}"}

# ═══════════════════════════════════════════════════════════
# Run Single Task
# ═══════════════════════════════════════════════════════════

def run_task(task_id: str) -> Dict[str, Any]:

    log_start(task=task_id, env=ENV_NAME, model=MODEL_NAME)

    # Reset environment
    try:
        resp = requests.post(
            f"{ENV_BASE_URL}/reset",
            json={"task_id": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        observation = resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to reset environment for {task_id}: {e}", flush=True)
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return {
            "task_id":        task_id,
            "steps":          0,
            "final_reward":   0.0,
            "success":        False,
            "rewards_per_step": [],
        }

    done               = False
    step_count         = 0
    rewards: List[float] = []
    final_reward       = 0.0
    success            = False
    conversation_history: List[Dict[str, str]] = []
    max_steps          = observation.get("max_steps", 15)

    while not done and step_count < max_steps:
        action = get_llm_action(observation, conversation_history)

        try:
            resp = requests.post(
                f"{ENV_BASE_URL}/step",
                json=action,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            print(f"[ERROR] Step failed: {e}", flush=True)
            break

        step_count  += 1
        reward       = float(result.get("reward", 0.0))
        done         = bool(result.get("done", False))
        success      = bool(result.get("success", False))
        observation  = result.get("observation", {})
        info         = result.get("info", {})
        error        = info.get("error", None)

        rewards.append(reward)
        final_reward = reward

        log_step(
            step=step_count,
            action_type=action["action_type"],
            value=action["value"],
            reward=reward,
            done=done,
            error=error,
        )

    # score is final_reward already in [0.0, 1.0]
    score = min(max(final_reward, 0.0), 1.0)
    log_end(success=success, steps=step_count, score=score, rewards=rewards)

    return {
        "task_id":          task_id,
        "steps":            step_count,
        "final_reward":     final_reward,
        "success":          success,
        "rewards_per_step": rewards,
    }

# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main() -> None:

    print("=" * 60, flush=True)
    print("SRE Incident Response — Baseline Inference Agent", flush=True)
    print(f"Model:       {MODEL_NAME}", flush=True)
    print(f"API Base:    {API_BASE_URL}", flush=True)
    print(f"Environment: {ENV_BASE_URL}", flush=True)
    print(f"API Key:     {'set' if API_KEY else 'NOT SET'}", flush=True)
    print("=" * 60, flush=True)

    results: List[Dict[str, Any]] = []

    for task_id in TASK_IDS:
        result = run_task(task_id)
        results.append(result)

    # Summary table
    total_reward = sum(r["final_reward"] for r in results)
    avg_reward   = total_reward / len(results) if results else 0.0

    print("\nBASELINE RESULTS SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"{'Task':<26}| {'Steps':>5} | {'Final Reward':>12} | {'Success':>7}", flush=True)
    print("-" * 60, flush=True)
    for r in results:
        print(
            f"{r['task_id']:<26}| {r['steps']:>5} | "
            f"{r['final_reward']:>12.2f} | {str(r['success']):>7}",
            flush=True,
        )
    print("=" * 60, flush=True)
    print(f"Average Score: {avg_reward:.2f}", flush=True)


if __name__ == "__main__":
    main()