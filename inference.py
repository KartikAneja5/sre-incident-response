"""
Inference Script — MANDATORY BASELINE
=====================================
STDOUT FORMAT (auto-grader parses these exact lines):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import os
import json
import time
from typing import List, Optional
from openai import OpenAI
from environment import SREEnvironment
from models import ActionModel

# ── Credentials (read strictly from env vars defined by OpenEnv rules) ──
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
BENCHMARK = "sre-incident-response"

if not API_KEY:
    print("WARNING: No API key found. Baseline evaluation will likely fail.", flush=True)

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY,
    timeout=60.0,
)

SYSTEM_PROMPT = """You are an expert on-call site reliability engineer (SRE).
You receive production incident alerts and must diagnose and fix them.
AVAILABLE ACTIONS (respond with ONLY valid JSON, no explanation):
- {"action_type": "acknowledge_alert", "value": "<alert description>"}
- {"action_type": "diagnose", "value": "<your diagnosis>"}
- {"action_type": "run_query", "value": "<query description>"}
- {"action_type": "apply_fix", "value": "<fix description>"}
- {"action_type": "escalate", "value": "<escalation reason>"}
- {"action_type": "write_postmortem", "value": "<postmortem content>"}
- {"action_type": "noop", "value": ""}
STRATEGY:
1. Read logs and check metrics BEFORE acting
2. Identify root cause (not just symptoms)
3. Fix in correct dependency order
4. Always write postmortem when resolved
Respond with ONLY a JSON object. No markdown, no explanation."""


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


def call_llm(messages: list, max_retries: int = 3) -> str:
    """Call LLM with retry + backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=256,
                temperature=0.1
            )
            text = (response.choices[0].message.content or "").strip()
            # Strip markdown code fences if model wraps its answer
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0].strip()
            return text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 15 * (attempt + 1)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Max retries exceeded for LLM call")


def run_episode(task_name: str) -> float:
    """Run a single task episode using the in-process SREEnvironment."""
    env = SREEnvironment()
    obs = env.reset(task_name)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    done = False
    steps_taken = 0
    score = 0.0
    rewards_list: List[float] = []

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    while not done:
        # Build user prompt from observation
        user_content = (
            f"INCIDENT STATUS — Step {obs.current_step}/{obs.max_steps}\n"
            f"GOAL: {obs.task_goal}\n\n"
            f"ACTIVE ALERTS:\n" +
            "\n".join(f"  {i+1}. {a}" for i, a in enumerate(obs.active_alerts)) +
            f"\n\nRECENT LOGS:\n" +
            "\n".join(f"  {log}" for log in obs.logs[-8:]) +
            f"\n\nMETRICS:\n" +
            "\n".join(f"  {k}: {v}" for k, v in obs.metrics.items()) +
            (f"\n\nHINT: {obs.hint}" if obs.hint else "") +
            '\n\nRespond with ONLY a JSON object: {"action_type": "...", "value": "..."}'
        )
        messages.append({"role": "user", "content": user_content})

        action_error: Optional[str] = None
        action_str = ""

        try:
            action_text = call_llm(messages)
            messages.append({"role": "assistant", "content": action_text})

            # Clean for single-line STDOUT
            action_str = action_text.replace("\n", "").replace("\r", "").replace(" ", "")

            action_dict = json.loads(action_text)
            action = ActionModel(
                action_type=action_dict.get("action_type", "noop"),
                value=str(action_dict.get("value", "")),
            )

        except json.JSONDecodeError:
            action_error = "ParseError"
            action = ActionModel(action_type="noop", value="parse error")
            action_str = "noop"
        except Exception as exc:
            action_error = "Exception"
            action = ActionModel(action_type="noop", value=str(exc))
            action_str = "noop"

        try:
            result = env.step(action)
            step_reward = result.reward
            done = result.done
            score = result.reward
        except Exception:
            step_reward = 0.0
            done = True
            action_error = "StepError"

        rewards_list.append(step_reward)
        steps_taken += 1

        log_step(step=steps_taken, action=action_str, reward=step_reward, done=done, error=action_error)

        # Rate-limit pause
        time.sleep(5)

    success = score > 0.1
    log_end(success=success, steps=steps_taken, score=score, rewards=rewards_list)
    return score


if __name__ == "__main__":
    tasks = ["alert_triage", "root_cause_diagnosis", "full_incident_runbook"]
    for task in tasks:
        run_episode(task)