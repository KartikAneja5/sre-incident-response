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
# Environment Variables
# ═══════════════════════════════════════════════════════════

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.getenv("HF_TOKEN")   # ← ONLY HF_TOKEN, no fallback
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")

# ═══════════════════════════════════════════════════════════
# OpenAI Client
# ═══════════════════════════════════════════════════════════

if not HF_TOKEN:
    print("WARNING: No API key found. Set HF_TOKEN environment variable.", flush=True)

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

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


def build_user_prompt(observation: Dict[str, Any]) -> str:
    """Build a user prompt from the observation data."""
    logs      = observation.get("logs", [])
    metrics   = observation.get("metrics", {})
    alerts    = observation.get("active_alerts", [])
    goal      = observation.get("task_goal", "")
    step      = observation.get("current_step", 0)
    max_steps = observation.get("max_steps", 10)
    hint      = observation.get("hint", "")

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
        '\nRespond with ONLY a JSON object: {"action_type": "...", "value": "..."}'
    )

    return "\n".join(prompt_parts)


def get_llm_action(
    observation: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
) -> Dict[str, str]:
    """Call the LLM to get the next action."""

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

        content = content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        action = json.loads(content)
        return {
            "action_type": action.get("action_type", "noop"),
            "value":       action.get("value", ""),
        }

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {"action_type": "noop", "value": f"Failed to parse LLM response: {e}"}
    except Exception as e:
        return {"action_type": "noop", "value": f"LLM call failed: {e}"}


def run_task(task_id: str) -> Dict[str, Any]:
    """Run a single task from start to finish."""

    print(f"[START] task={task_id} env=sre-incident-response model={MODEL_NAME}", flush=True)

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
        print(f"[ERROR] Failed to reset environment: {e}", flush=True)
        print(f"[END]   success=false steps=0 score=0.00 rewards=", flush=True)
        return {
            "task_id":          task_id,
            "steps":            0,
            "final_reward":     0.0,
            "success":          False,
            "rewards_per_step": [],
        }

    done         = False
    step_count   = 0
    rewards: List[float] = []
    final_reward = 0.0
    success      = False
    conversation_history: List[Dict[str, str]] = []

    while not done:
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
        reward       = result.get("reward", 0.0)
        done         = result.get("done", False)
        success      = result.get("success", False)
        observation  = result.get("observation", {})
        info         = result.get("info", {})
        error        = info.get("error", None)

        rewards.append(reward)
        final_reward = reward

        display_value = action["value"][:80].replace("\n", " ").replace("'", "")
        print(
            f"[STEP]  step={step_count} "
            f"action={action['action_type']}('{display_value}') "
            f"reward={reward:.2f} done={str(done).lower()} "
            f"error={error if error else 'null'}",
            flush=True,
        )

    score       = min(max(final_reward, 0.0), 1.0)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END]   success={str(success).lower()} "
        f"steps={step_count} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )

    return {
        "task_id":          task_id,
        "steps":            step_count,
        "final_reward":     final_reward,
        "success":          success,
        "rewards_per_step": rewards,
    }


def main() -> None:
    """Run all 3 tasks sequentially."""

    print("=" * 60, flush=True)
    print("SRE Incident Response — Baseline Inference Agent",  flush=True)
    print(f"Model:       {MODEL_NAME}",                        flush=True)
    print(f"API Base:    {API_BASE_URL}",                      flush=True)
    print(f"Environment: {ENV_BASE_URL}",                      flush=True)
    print(f"API Key:     {'set' if HF_TOKEN else 'NOT SET'}", flush=True)
    print("=" * 60, flush=True)

    results: List[Dict[str, Any]] = []

    for task_id in TASK_IDS:
        result = run_task(task_id)
        results.append(result)

    total_reward = sum(r["final_reward"] for r in results)
    avg_reward   = total_reward / len(results) if results else 0.0

    print("\nBASELINE RESULTS SUMMARY",                                        flush=True)
    print("=" * 60,                                                             flush=True)
    print(f"{'Task':<26}| {'Steps':>5} | {'Final Reward':>12} | {'Success':>7}", flush=True)
    print("-" * 60,                                                             flush=True)
    for r in results:
        print(
            f"{r['task_id']:<26}| {r['steps']:>5} | "
            f"{r['final_reward']:>12.2f} | {str(r['success']):>7}",
            flush=True,
        )
    print("=" * 60,                   flush=True)
    print(f"Average Score: {avg_reward:.2f}", flush=True)


if __name__ == "__main__":
    main()