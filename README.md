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
  - real-world
  - rl
  - agent-evaluation
---

# 🚨 SRE Incident Response — OpenEnv Environment

<div align="center">

![Status](https://img.shields.io/badge/status-live-brightgreen?style=for-the-badge)
![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-blue?style=for-the-badge)
![Tasks](https://img.shields.io/badge/tasks-3-orange?style=for-the-badge)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/python-3.11-yellow?style=for-the-badge&logo=python)

**An AI agent environment where agents act as on-call SRE engineers.**  
Triage alerts → Diagnose root causes → Apply fixes → Write postmortems.

[🌐 Live Demo](https://huggingface.co/spaces/kartikaneja5/sre-incident-response) · [📖 API Docs](https://kartikaneja5-sre-incident-response.hf.space/docs) · [⭐ GitHub](https://github.com/KartikAneja5/sre-incident-response)

</div>

---

## 🎯 Why This Environment?

Site Reliability Engineering is one of the most demanding disciplines in software engineering. On-call engineers must process information from multiple sources simultaneously — logs, metrics, dashboards, and alerts — and make high-stakes decisions under extreme time pressure.

> **This environment directly tests skills that matter in production.**  
> Every scenario is grounded in real failure patterns that engineers encounter daily at companies like Google, Meta, and Netflix.

This makes it uniquely valuable for:
- **Training agents** to reason about complex, multi-signal technical problems
- **Evaluating LLMs** on real-world SRE knowledge and diagnostic reasoning
- **Benchmarking** how well models handle cascading failures vs. isolated incidents
- **Studying** whether agents can correctly prioritize and sequence remediation steps

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent (LLM / RL Policy)                  │
│                                                             │
│  observe: logs + metrics + alerts                           │
│  act:     acknowledge | diagnose | apply_fix | postmortem   │
└─────────────────────┬───────────────────────────────────────┘
                      │ OpenEnv API (step/reset/state)
┌─────────────────────▼───────────────────────────────────────┐
│              SRE Incident Response Environment              │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ alert_triage │  │ root_cause   │  │ full_incident    │  │
│  │   (Easy)     │  │  (Medium)    │  │ _runbook (Hard)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  Fuzzy Graders → Partial Rewards → Episode State           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎮 Three Tasks — Easy to Hard

### Task 1: Alert Triage `alert_triage` — 🟢 Easy (8 steps)

**Scenario:** 5 alerts firing simultaneously across a production microservices stack. Database CPU is at 98%, causing a cascade of downstream failures across payment, auth, cache, and API gateway services.

**The Challenge:** Most alerts are *symptoms*, not causes. The agent must distinguish root cause from noise.

```
Services Involved:
  db-primary      → CPU 98%, slow queries, queue depth 847
  payment-service → Error rate 34.2%, connection timeouts
  auth-service    → p99 latency 890ms (SLA: 200ms)
  cache-redis     → Cache miss rate 67% (normally <10%)
  api-gateway     → 503 rate at 28.5% and climbing
```

**Grading Criteria (8 criteria, max 1.0):**

| Criterion | Points |
|-----------|--------|
| Acknowledge db-primary as critical root cause | +0.15 |
| Classify db-primary as P1 | +0.15 |
| Classify payment-service as P1 | +0.10 |
| Classify auth-service as P2 | +0.10 |
| Classify cache-redis as P2 | +0.10 |
| Classify api-gateway as P3 | +0.10 |
| Diagnose db CPU overload as root cause | +0.15 |
| Identify cascading failure pattern | +0.15 |

---

### Task 2: Root Cause Diagnosis `root_cause_diagnosis` — 🟡 Medium (10 steps)

**Scenario:** Payment service is completely down (HTTP 503). Incident started 2 hours ago. The failure chain: bad deploy (v2.4.1) → slow SQL query → DB connection pool exhausted → 503s.

**The Challenge:** The agent must actively investigate using `run_query` actions to gather evidence before diagnosing. This tests whether agents explore before concluding.

**Available Queries:**
```
"slow queries"      → Returns 47s slow query logs
"recent deploy"     → Returns v2.4.1 deployment at 01:23 UTC
"connection pool"   → Returns pool at 98% capacity (490/500)
"payment logs"      → Returns FATAL connection timeout logs
```

**Grading Criteria (5 criteria, max 1.0):**

| Criterion | Points |
|-----------|--------|
| Identify the slow query | +0.20 |
| Link issue to deploy v2.4.1 | +0.20 |
| Identify connection pool exhaustion | +0.20 |
| Acknowledge correct root cause alert | +0.20 |
| Suggest correct fix (rollback/revert) | +0.20 |

---

### Task 3: Full Incident Runbook `full_incident_runbook` — 🔴 Hard (20 steps)

**Scenario:** Company-wide login outage. Three services failing simultaneously with a non-obvious cascade chain. Root cause: Redis OOM with `noeviction` policy.

**The Cascade Chain:**
```
Redis OOM (noeviction)
    ↓
Auth service cache writes rejected
    ↓
Auth enters retry storm → CPU at 94%
    ↓
Auth DB fallback also fails (pool exhausted)
    ↓
Mobile API receives 503s from auth
    ↓
Circuit breaker OPENS on mobile API
    ↓
100% of logins failing company-wide ← SEV1
```

**Red Herring:** `WARNING: api-gateway connection pool at 75%` — a misleading alert that wastes steps if the agent investigates it.

**The Challenge:** Correct fix ORDER matters. Redis must be fixed before auth, auth before mobile-api. A wrong order gives no reward for ordering criterion.

**Grading Criteria (9 criteria, max 1.0):**

| Criterion | Points |
|-----------|--------|
| Triage redis as P1 root cause | +0.10 |
| Triage auth-service as P1 secondary | +0.10 |
| Diagnose Redis OOM as origin | +0.15 |
| Diagnose cascade chain correctly | +0.15 |
| Apply Redis memory fix | +0.10 |
| Apply auth-service recovery | +0.10 |
| Apply fixes in CORRECT ORDER | +0.10 |
| Postmortem includes timeline | +0.10 |
| Postmortem includes RCA section | +0.10 |

---

## 📊 Baseline Scores

Evaluated with **Qwen/Qwen2.5-72B-Instruct** via HuggingFace router (zero-shot):

| Task | Steps | Final Score | Success |
|------|-------|-------------|---------|
| `alert_triage` | 5 | **1.00** | ✅ |
| `root_cause_diagnosis` | 4 | **1.00** | ✅ |
| `full_incident_runbook` | 6 | **1.00** | ✅ |
| **Average** | **5** | **1.00** | **3/3** |

> Even when the model used invalid action types (e.g. `classify_alerts`), the environment handled them gracefully with `error=invalid action_type` — without crashing — and the fuzzy grader still picked up the intent from valid subsequent actions.

---

## 🏗️ Observation Space

Each step the agent receives a rich observation:

```json
{
  "logs": [
    "[2026-04-10 03:12:01 UTC] [db-primary] CRITICAL: CPU utilization at 98.2%",
    "[2026-04-10 03:12:03 UTC] [db-primary] WARN: Slow query detected — 34.7s",
    "[2026-04-10 03:12:08 UTC] [payment-service] ERROR: Connection timeout (1/3)"
  ],
  "metrics": {
    "db_cpu_percent": 98.0,
    "payment_error_rate": 34.2,
    "auth_latency_ms": 890.0,
    "cache_miss_rate": 67.0,
    "db_connection_queue": 847.0
  },
  "active_alerts": [
    "CRITICAL: db-primary CPU > 95%",
    "CRITICAL: payment-service error rate > 30%",
    "WARNING: auth-service p99 latency > 800ms"
  ],
  "task_goal": "Triage 5 simultaneous alerts and identify the root cause.",
  "current_step": 1,
  "max_steps": 8,
  "available_actions": ["acknowledge_alert", "diagnose", "run_query", "apply_fix", ...],
  "hint": "Look at which service failure could cause ALL other alerts.",
  "session_id": "5942d1b9-dd11-476e-8d10-8fb7dfb98e98"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `logs` | `List[str]` | Last 10 timestamped log lines from affected services |
| `metrics` | `Dict[str, float]` | Real-time service metrics (CPU, latency, error rates) |
| `active_alerts` | `List[str]` | Currently firing alerts with severity prefixes |
| `task_goal` | `str` | What the agent must accomplish this episode |
| `current_step` | `int` | Step number in the episode |
| `max_steps` | `int` | Maximum steps before episode ends |
| `time_elapsed_seconds` | `float` | Simulated incident elapsed time |
| `available_actions` | `List[str]` | Valid action_type values |
| `hint` | `Optional[str]` | Grader feedback from last action |
| `session_id` | `Optional[str]` | Unique session identifier |

---

## ⚡ Action Space

The agent submits actions as JSON:

```json
{"action_type": "diagnose", "value": "Root cause: db-primary CPU overload at 98% causing cascading failures to all downstream services"}
```

| Action Type | Purpose | Example Value |
|-------------|---------|---------------|
| `acknowledge_alert` | Acknowledge & classify a specific alert | `"CRITICAL: db-primary CPU > 95% — P1 root cause"` |
| `diagnose` | State root cause analysis | `"db-primary CPU overload causing cascade"` |
| `run_query` | Query logs for more info (Tasks 2 & 3) | `"slow queries"`, `"recent deploy"` |
| `apply_fix` | Apply a remediation action | `"Rollback deploy to v2.4.0"` |
| `escalate` | Page another team | `"Escalating to DBA team"` |
| `write_postmortem` | Submit incident postmortem | Full postmortem with timeline and RCA |
| `noop` | Take no action | `""` |

---

## 💰 Reward Function Design

Rewards are **cumulative and partial** — never binary.

```python
# Each criterion satisfied adds its weight to total reward
# Same criterion NEVER rewarded twice
# Reward always in [0.0, 1.0]

reward_0.15  → acknowledge root cause alert
reward_0.30  → classify db-primary P1
reward_0.40  → classify payment-service P1
...
reward_1.00  → episode complete ✅
```

**Penalties (to discourage bad behavior):**
```
-0.05  apply_fix before root cause identified
-0.05  escalate when reward already > 0.5 (unnecessary escalation)
-0.02  noop after step 5 (penalizes stalling)
 0.00  minimum reward floor (never goes negative)
```

**Episode ends when:**
- Total reward ≥ 0.95 (practical completion), OR
- Maximum steps reached (`done=True`, `success=False` if reward < 0.5)

---

## 🌟 Key Design Decisions

### 1. Fuzzy Grading — No Exact String Matching
```python
# Agent doesn't need to say exact phrases
# "db cpu is overloaded" → matches keywords → reward granted
def matches_any(text: str, keywords: List[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)
```

### 2. Thread-Safe Session Management
```python
# Each /reset creates a completely isolated session
# Up to 50 concurrent sessions supported
# Oldest sessions auto-evicted (LRU)
sessions: OrderedDict[str, SREEnvironment] = OrderedDict()
```

### 3. Red Herring In Hard Task
Task 3 deliberately includes a misleading alert (`api-gateway connection pool at 75%`) that agents commonly investigate — wasting steps — before finding the real Redis OOM root cause. This makes the hard task genuinely challenging for frontier models.

### 4. Conversation Memory In Inference
The baseline inference script maintains conversation history across steps — the LLM remembers what it diagnosed in step 1 when applying a fix in step 6. This is how real SRE workflows work.

---

## 🚀 Setup & Installation

### Option 1 — Local (pip)

```bash
git clone https://github.com/KartikAneja5/sre-incident-response.git
cd sre-incident-response

pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000

# Test it's alive
curl http://localhost:8000/health
```

### Option 2 — Docker (Recommended)

```bash
docker build -t sre-env .

# Map 8000 → internal port 7860
docker run -p 8000:7860 sre-env

curl http://localhost:8000/health
# {"status":"ok","environment":"sre-incident-response","version":"1.0.0","tasks_available":3}
```

### Option 3 — HuggingFace Space (Live Now)

```bash
curl https://kartikaneja5-sre-incident-response.hf.space/health
```

---

## 🧪 Running the Baseline

```bash
# With HuggingFace router (recommended)
export HF_TOKEN=your_hf_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_BASE_URL=http://localhost:8000

python inference.py
```

**Expected output:**
```
[START] task=alert_triage env=sre-incident-response model=Qwen/Qwen2.5-72B-Instruct
[STEP]  step=1 action=acknowledge_alert('CRITICAL: db-primary CPU > 95%') reward=0.30 done=false error=null
[STEP]  step=2 action=diagnose('db-primary CPU overload causing cascading failures') reward=0.45 done=false error=null
[STEP]  step=3 action=diagnose('payment-service P1 downstream impact') reward=0.70 done=false error=null
[STEP]  step=4 action=diagnose('auth-service P2 secondary') reward=0.80 done=false error=null
[STEP]  step=5 action=diagnose('cascade from db to all services') reward=1.00 done=true error=null
[END]   success=true steps=5 score=1.00 rewards=0.30,0.45,0.70,0.80,1.00
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `https://router.huggingface.co/v1` | LLM API endpoint |
| `MODEL_NAME` | `Qwen/Qwen2.5-72B-Instruct` | Model identifier |
| `HF_TOKEN` | — | HuggingFace / API key |
| `ENV_BASE_URL` | `http://localhost:8000` | Environment server URL |

---

## 🔌 API Reference

### `GET /health`
```json
{
  "status": "ok",
  "environment": "sre-incident-response",
  "version": "1.0.0",
  "tasks_available": 3,
  "active_sessions": 2
}
```

### `GET /metrics`
```json
{
  "total_resets": 47,
  "total_steps": 312,
  "total_episodes_completed": 41,
  "average_final_reward": 0.847,
  "active_sessions": 2
}
```

### `POST /reset`
```bash
curl -X POST /reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "alert_triage"}'
```
Returns: `ObservationModel` + `X-Session-ID` response header

### `POST /step`
```bash
curl -X POST /step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "diagnose", "value": "db-primary CPU overload"}'
```
Returns: `StepResultModel` with `reward`, `done`, `success`, `info`

### `GET /state`
Returns: Current task, episode ID, step count, cumulative reward, per-criterion grader scores

### `GET /tasks`
Returns: All 3 task definitions with difficulty, max_steps, description

### `GET /docs`
Returns: Interactive Swagger UI for all endpoints

---

## 📁 Project Structure

```
sre-incident-response/
├── main.py                  ← FastAPI app — all endpoints, session management
├── environment.py           ← SREEnvironment class — state management, episode logic
├── models.py                ← Pydantic v2 models — fully typed
├── inference.py             ← Baseline LLM agent — OpenAI client
├── openenv.yaml             ← OpenEnv spec metadata
├── Dockerfile               ← Production image (python:3.11-slim, port 7860)
├── requirements.txt         ← Pinned dependencies
├── pyproject.toml           ← Package metadata + openenv entry points
├── uv.lock                  ← Reproducible dependency lock
│
├── tasks/
│   ├── __init__.py          ← Task registry
│   ├── base_task.py         ← Abstract Task base class
│   ├── alert_triage.py      ← Task 1: Alert Triage (Easy)
│   ├── root_cause.py        ← Task 2: Root Cause Diagnosis (Medium)
│   └── full_runbook.py      ← Task 3: Full Incident Runbook (Hard)
│
├── graders/
│   ├── __init__.py
│   └── base_grader.py       ← Fuzzy matching grader logic
│
├── data/
│   ├── __init__.py
│   └── scenarios.py         ← All synthetic scenario data
│
└── server/
    ├── __init__.py
    └── app.py               ← OpenEnv server entry point
```

---

## 🔒 OpenEnv Spec Compliance

```bash
$ openenv validate
[OK] sre-incident-response: Ready for multi-mode deployment
```

| Requirement | Status |
|-------------|--------|
| Typed Pydantic models | ✅ |
| `POST /reset` → `ObservationModel` | ✅ |
| `POST /step` → `StepResultModel` | ✅ |
| `GET /state` → `StateModel` | ✅ |
| `openenv.yaml` valid | ✅ |
| `pyproject.toml` with server entry point | ✅ |
| `uv.lock` present | ✅ |
| 3+ tasks with graders | ✅ |
| Scores in `[0.0, 1.0]` | ✅ |
| Docker builds cleanly | ✅ |
| HF Space live | ✅ |

---

## 🧠 What Makes This Hard For Frontier Models

| Challenge | Why It's Hard |
|-----------|---------------|
| **Multi-signal correlation** | 5+ simultaneous alerts — most are symptoms, not causes |
| **Red herrings** | Task 3 has misleading alerts that waste steps |
| **Ordering constraints** | Fix order matters — wrong sequence = no reward |
| **Active investigation** | Task 2 requires `run_query` before diagnosing — passive agents fail |
| **Postmortem writing** | Structured document with specific required sections |
| **Cascading failure chains** | 3+ service failures with non-obvious root cause linkage |

---

## 🏆 Built For

**Meta × Hugging Face OpenEnv Hackathon 2026**

Built using the [OpenEnv](https://github.com/huggingface/openenv) framework.

---

## 📄 License

MIT — Built by [Kartik Aneja](https://github.com/KartikAneja5) and [Nihal Joshi](https://github.com/Nihal040806)