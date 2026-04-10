---
title: SRE Incident Response
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: mit
tags:
  - openenv
  - sre
  - incident-response
  - devops
---

# SRE Incident Response — OpenEnv Environment

An AI agent environment where agents act as on-call SRE (Site Reliability Engineering) engineers. Agents receive realistic synthetic server logs, metrics, and alerts and must triage, diagnose, fix, and document production incidents.

Built for the **Meta × Hugging Face Hackathon** using the [OpenEnv](https://github.com/huggingface/openenv) framework.

---

## Overview & Motivation

Site Reliability Engineering is one of the most demanding disciplines in software engineering. On-call engineers must rapidly process information from multiple sources — logs, metrics, dashboards, and alerts — to diagnose and resolve production incidents under extreme time pressure.

This environment simulates that experience with three progressively challenging scenarios, designed to evaluate an AI agent's ability to:

- **Triage** multiple simultaneous alerts by severity and impact
- **Diagnose** root causes from noisy, real-world-style log data
- **Apply fixes** in the correct order to resolve cascading failures
- **Document** incidents with proper postmortem structure

Each scenario is grounded in real-world failure patterns that production engineers encounter daily.

---

## Environment Description

The environment presents agents with:

1. **Synthetic server logs** — realistic timestamped log lines from multiple services
2. **Service metrics** — numeric indicators (CPU%, latency, error rates, etc.)
3. **Active alerts** — prioritized alerts with severity levels
4. **A clear goal** — what the agent needs to accomplish

The agent interacts through a step-based API: observe → act → receive feedback, with cumulative partial rewards based on how well the agent addresses each grading criterion.

---

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `logs` | `List[str]` | Last 10 relevant log lines from affected services |
| `metrics` | `Dict[str, float]` | Service metrics (CPU, latency, error rate, etc.) |
| `active_alerts` | `List[str]` | Currently firing alerts with severity prefixes |
| `task_goal` | `str` | Description of what the agent must accomplish |
| `current_step` | `int` | Current step number in the episode |
| `max_steps` | `int` | Maximum steps allowed for the episode |
| `time_elapsed_seconds` | `float` | Simulated incident elapsed time |
| `available_actions` | `List[str]` | Valid action_type values |
| `hint` | `Optional[str]` | Optional debugging hint or feedback from the last action |

---

## Action Space

The agent submits actions as JSON with two fields:

```json
{
  "action_type": "diagnose",
  "value": "Root cause is db-primary CPU overload causing cascading failures"
}
```

### Action Types

| Action Type | Purpose | Example Value |
|-------------|---------|---------------|
| `acknowledge_alert` | Acknowledge and classify a specific alert | `"CRITICAL: db-primary CPU > 95% — P1 root cause"` |
| `diagnose` | Provide a diagnosis or root cause analysis | `"db-primary CPU overload causing cascade to payment and auth"` |
| `run_query` | Query for specific log data (Tasks 2 & 3) | `"slow queries"`, `"recent deploy"`, `"redis memory"` |
| `apply_fix` | Apply a remediation action | `"Rollback to v2.4.0"`, `"Change Redis eviction policy"` |
| `escalate` | Escalate to another team | `"Escalating to DBA team for query optimization"` |
| `write_postmortem` | Submit incident postmortem | Full postmortem text with timeline and RCA |
| `noop` | Take no action | `""` |

---

## Tasks

### Task 1: Alert Triage (Easy) — 8 Steps Max

**Scenario:** 5 alerts firing simultaneously across a microservices stack (payment-service, db-primary, cache-redis, auth-service, api-gateway). The real root cause is db-primary CPU at 98% causing cascading failures.

**Grading Criteria:**
- Acknowledge db-primary as the critical root cause alert (+0.15)
- Correctly classify db-primary as P1 (+0.15)
- Correctly classify payment-service as P1 (+0.10)
- Correctly classify auth-service as P2 (+0.10)
- Correctly classify cache-redis as P2 (+0.10)
- Correctly classify api-gateway as P3 (+0.10)
- Diagnose db CPU overload as root cause (+0.15)
- Identify cascading failure pattern (+0.15)

---

### Task 2: Root Cause Diagnosis (Medium) — 10 Steps Max

**Scenario:** Payment service is completely down (HTTP 503). A bad deploy (v2.4.1) introduced a slow SQL query that exhausted the DB connection pool.

**Key Feature:** Agents can use `run_query` to investigate:
- `"slow queries"` — returns slow query log data
- `"deploy"` / `"recent deploy"` — returns deployment history
- `"connection pool"` — returns pool status information
- `"payment logs"` — returns payment service errors

**Grading Criteria:**
- Identify the slow query (+0.20)
- Link issue to deploy v2.4.1 (+0.20)
- Identify connection pool exhaustion (+0.20)
- Acknowledge the correct alert (+0.20)
- Suggest correct fix (rollback/revert) (+0.20)

---

### Task 3: Full Incident Runbook (Hard) — 15 Steps Max

**Scenario:** Redis OOM → auth cache miss storm → auth CPU spike → mobile API circuit breaker → company-wide login outage. Root cause: Redis maxmemory policy set to `noeviction`.

**Grading Criteria:**
- Triage redis as P1 root cause (+0.10)
- Triage auth-service as P1 secondary (+0.10)
- Diagnose Redis OOM as origin (+0.15)
- Diagnose cascade chain correctly (+0.15)
- Apply Redis memory fix (+0.10)
- Apply auth-service recovery fix (+0.10)
- Apply fixes in correct ORDER (+0.10)
- Postmortem includes timeline (+0.10)
- Postmortem includes root cause analysis (+0.10)

---

## Reward Function

Rewards are **cumulative and partial** — never just 0 or 1.

- Each grading criterion has a specific weight (listed above)
- When an action satisfies a criterion for the first time, that weight is added to the total
- The same criterion is never rewarded twice
- Total reward ranges from 0.0 to 1.0

**Penalties:**
- `-0.05` for applying a fix before identifying the root cause
- `-0.05` for escalating when the reward is already > 0.5
- `-0.02` per noop after step 5
- Reward floor is 0.0 (penalties cannot make it negative)

**Episode ends when:**
- Total reward ≥ 0.95 (practical completion), OR
- Maximum steps reached

---

## Setup & Installation

### Local (pip)

```bash
# Clone the repository
git clone https://github.com/your-name/sre-incident-response.git
cd sre-incident-response

# Install dependencies
pip install -r requirements.txt

# Start the environment server
uvicorn main:app --host 0.0.0.0 --port 8000

# In another terminal, run the baseline
export OPENAI_API_KEY=your-key-here
python inference.py
```

### Docker

```bash
# Build the image
docker build -t sre-env .

# Run the container
docker run -p 8000:8000 sre-env

# Test the health endpoint
curl http://localhost:8000/health

# Run inference against the container
export OPENAI_API_KEY=your-key-here
python inference.py
```

### Hugging Face Spaces

Deploy as a Docker Space on Hugging Face:

1. Create a new Space with "Docker" SDK
2. Upload all project files
3. Set the port to 8000 in Space settings
4. The environment will be available at your Space URL

---

## Running the Baseline

```bash
# Set your API key
export OPENAI_API_KEY=your-key-here

# Or for Hugging Face inference
export HF_TOKEN=your-hf-token
export API_BASE_URL=https://api-inference.huggingface.co/v1
export MODEL_NAME=meta-llama/Llama-3.3-70B-Instruct

# Run inference
python inference.py
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `MODEL_NAME` | `gpt-4o` | Model name to use |
| `HF_TOKEN` | — | Hugging Face token (or `OPENAI_API_KEY`) |
| `ENV_BASE_URL` | `http://localhost:8000` | Environment server URL |

---

## Baseline Scores

With GPT-4o (no few-shot, zero-shot prompting):

| Task | Steps | Final Reward | Success |
|------|-------|-------------|---------|
| alert_triage | ~5 | ~0.85 | ✓ |
| root_cause_diagnosis | ~7 | ~0.80 | ✓ |
| full_incident_runbook | ~12 | ~0.65 | ✓ |

**Average Score: ~0.77**

---

## Environment API Reference

### `GET /health`
Returns `{"status": "ok"}`. Always responds with HTTP 200.

### `POST /reset`
**Body:** `{"task_id": "alert_triage"}`
**Response:** `ObservationModel` — initial observation for the episode.

### `POST /step`
**Body:** `{"action_type": "diagnose", "value": "..."}`
**Response:** `StepResultModel` — observation, reward, done flag, success, and info.

### `GET /state`
**Response:** `StateModel` — current task, episode, step, reward, and grader scores.

### `GET /tasks`
**Response:** List of `TaskInfo` objects with id, name, difficulty, max_steps, and description.

---

## File Structure

```
sre-incident-response/
├── main.py                      ← FastAPI app with all endpoints
├── environment.py               ← SREEnvironment class, state management
├── models.py                    ← All Pydantic v2 models
├── tasks/
│   ├── __init__.py              ← Task registry
│   ├── base_task.py             ← Abstract base Task class
│   ├── alert_triage.py          ← Task 1: Alert Triage (Easy)
│   ├── root_cause.py            ← Task 2: Root Cause Diagnosis (Medium)
│   └── full_runbook.py          ← Task 3: Full Incident Runbook (Hard)
├── data/
│   ├── __init__.py
│   └── scenarios.py             ← All synthetic scenario data
├── graders/
│   ├── __init__.py
│   └── base_grader.py           ← Grading logic with fuzzy matching
├── inference.py                 ← Baseline agent (root dir)
├── openenv.yaml                 ← OpenEnv specification
├── Dockerfile                   ← Production Docker image
├── requirements.txt             ← Pinned dependencies
└── README.md                    ← This file
```

---

## License

MIT
