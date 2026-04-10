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

# ── Credentials (read strictly from env vars — DO NOT hardcode or add fallbacks) ──
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")
BENCHMARK    = "sre-incident-response"

if HF_TOKEN is None:
    print("WARNING: HF_TOKEN not found. Baseline evaluation will likely fail.", flush=True)

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
    timeout=60.0,
)

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert on-call SRE engineer responding to a production incident.
You will receive logs, metrics, and alerts. You must take actions to triage,
diagnose, and resolve the incident.
AVAILABLE ACTION TYPES:
  acknowledge_alert  — acknowledge a firing alert
  diagnose           — state your diagnosis of the root cause
  run_query          — query logs for more information
  apply_fix          — apply a remediation step
  escalate           — escalate to another team
  write_postmortem   — write a postmortem document
  noop               — do nothing
Respond with ONLY a valid JSON object, no explanation, no markdown:
{"action_type": "diagnose", "value": "your diagnosis here"}"""


# ── Logging helpers ────────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(
        f"[STEP] step={step} action={action} "
        f"reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── LLM call with retry ────────────────────────────────────────────────────────

def call_llm(messages: list, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=256,
                temperature=0.1,
            )
            text = (response.choices[0].message.content or "").strip()
            # Strip markdown code fences if model wraps answer
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


# ── Single episode ─────────────────────────────────────────────────────────────

def run_episode(task_name: str) -> float:
    env = SREEnvironment(task_id=task_name)
    obs = env.reset()

    messages     = [{"role": "system", "content": SYSTEM_PROMPT}]
    done         = False
    steps_taken  = 0
    score        = 0.0
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
        action_str   = ""

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
            action       = ActionModel(action_type="noop", value="parse error")
            action_str   = '{"action_type":"noop","value":"parse_error"}'
        except Exception as exc:
            action_error = "Exception"
            action       = ActionModel(action_type="noop", value=str(exc))
            action_str   = '{"action_type":"noop","value":"exception"}'

        try:
            result      = env.step(action)
            step_reward = result.reward
            done        = result.done
            score       = result.reward
            obs         = result.observation
            info        = result.info
            if info.get("error"):
                action_error = info["error"]
        except Exception:
            step_reward  = 0.0
            done         = True
            action_error = "StepError"

        rewards_list.append(step_reward)
        steps_taken += 1

        log_step(
            step=steps_taken,
            action=action_str,
            reward=step_reward,
            done=done,
            error=action_error,
        )

        # Small pause to avoid rate limits
        time.sleep(5)

    success = score > 0.1
    log_end(success=success, steps=steps_taken, score=score, rewards=rewards_list)
    return score


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tasks = ["alert_triage", "root_cause_diagnosis", "full_incident_runbook"]

    results = []
    for task in tasks:
        final_score = run_episode(task)
        results.append((task, final_score))

    print("\nBASELINE RESULTS SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"{'Task':<30} | {'Score':>6}", flush=True)
    print("-" * 60, flush=True)
    for task, score in results:
        print(f"{task:<30} | {score:>6.2f}", flush=True)
    print("=" * 60, flush=True)
    avg = sum(s for _, s in results) / len(results) if results else 0.0
    print(f"Average Score: {avg:.2f}", flush=True)