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
  - llm-evaluation
---

<div align="center">

# 🚨 SRE Incident Response
### OpenEnv Environment — Meta × Hugging Face Hackathon 2026

![Status](https://img.shields.io/badge/status-live-brightgreen?style=for-the-badge)
![OpenEnv](https://img.shields.io/badge/OpenEnv-validated-blue?style=for-the-badge)
![Tests](https://img.shields.io/badge/tests-29%20passing-success?style=for-the-badge)
![Tasks](https://img.shields.io/badge/tasks-3-orange?style=for-the-badge)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/python-3.11-yellow?style=for-the-badge&logo=python)

**An AI agent environment where agents act as on-call SRE engineers.**

Triage alerts → Diagnose root causes → Apply fixes in correct order → Write postmortems

[🌐 Live Space](https://huggingface.co/spaces/kartikaneja5/sre-incident-response) · [📖 API Docs](https://kartikaneja5-sre-incident-response.hf.space/docs) · [📊 Metrics](https://kartikaneja5-sre-incident-response.hf.space/metrics) · [⭐ GitHub](https://github.com/KartikAneja5/sre-incident-response)

</div>

---

## 🎯 Why This Environment Exists

Every SRE engineer has lived this nightmare: it's 3 AM, five alerts are firing simultaneously, and you have minutes to figure out which one is the root cause before your company's revenue tanks. You're correlating logs, metrics, and alerts across a dozen services — all in your head — under extreme pressure.

**This environment simulates exactly that.**

Unlike toy problems or synthetic benchmarks, every scenario in this environment is grounded in real failure patterns that engineers at Google, Meta, Netflix, and Stripe encounter in production weekly. The cascading failure chains, the misleading red herring alerts, the fix ordering constraints — all of it is real.

> **Why it matters for AI evaluation:** SRE incident response requires multi-signal reasoning, causal inference, temporal ordering, and domain knowledge simultaneously. It's one of the hardest real-world tasks for language models — and one of the most valuable to get right.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    AI Agent (LLM / RL Policy)                    │
│                                                                  │
│  Input:  logs + metrics + active_alerts + task_goal + hint       │
│  Output: {"action_type": "diagnose", "value": "..."}             │
└─────────────────────────┬────────────────────────────────────────┘
                          │  OpenEnv API
          ┌───────────────▼───────────────────┐
          │     FastAPI Environment Server     │
          │        (port 7860, Docker)         │
          │                                   │
          │  POST /reset  → ObservationModel  │
          │  POST /step   → StepResultModel   │
          │  GET  /state  → StateModel        │
          │  GET  /tasks  → List[TaskInfo]    │
          │  GET  /health → HealthModel       │
          │  GET  /metrics→ MetricsModel      │
          └───────────────┬───────────────────┘
                          │
          ┌───────────────▼───────────────────┐
          │     Session-Isolated Episodes      │
          │   (OrderedDict, max 50 sessions)   │
          │                                   │
          │  ┌──────────┐ ┌──────────┐ ┌────┐ │
          │  │ Task 1   │ │ Task 2   │ │ T3 │ │
          │  │  Easy    │ │  Medium  │ │Hard│ │
          │  └──────────┘ └──────────┘ └────┘ │
          │                                   │
          │     Fuzzy Graders + Partial Rewards│
          └───────────────────────────────────┘
```

---

## 🎮 Three Tasks — Designed For Real Evaluation

### 📗 Task 1: Alert Triage `alert_triage` — Easy (8 steps max)

**The Scenario:** Five alerts fire simultaneously across a production microservices stack. Database CPU hits 98%, triggering a cascade of downstream failures. Most alerts are *symptoms*. Only one is the *cause*.

**What makes it non-trivial:** Agents must distinguish root cause from noise across 5 services, classify severity correctly (P1/P2/P3), and articulate the cascade pattern — all within 8 steps.

**Scenario Variants:**
- `v0` — DB CPU overload cascading to payment, auth, cache, gateway
- `v1` — Auth service memory exhaustion cascading to mobile API

```
Services:  db-primary → payment-service → auth-service → cache-redis → api-gateway
Cascade:   CPU 98% → connection queue 847 → timeouts → latency spikes → 503s
```

**Grading (8 criteria, total = 1.0):**

| Criterion | Weight |
|-----------|--------|
| Acknowledge db-primary as P1 root cause | 0.15 |
| Classify db-primary as P1 | 0.15 |
| Classify payment-service as P1 | 0.10 |
| Classify auth-service as P2 | 0.10 |
| Classify cache-redis as P2 | 0.10 |
| Classify api-gateway as P3 | 0.10 |
| Diagnose db CPU overload as root cause | 0.15 |
| Identify cascading failure pattern | 0.15 |

---

### 📙 Task 2: Root Cause Diagnosis `root_cause_diagnosis` — Medium (10 steps max)

**The Scenario:** Payment service is completely down (HTTP 503). Incident started 2 hours ago. The failure chain is non-obvious: a bad deploy introduced a slow SQL query → exhausted DB connection pool → 503s.

**What makes it non-trivial:** Agents must actively *investigate* using `run_query` before diagnosing. Passive agents that skip investigation fail. The evidence is spread across deployment logs, slow query logs, and connection pool metrics.

**Scenario Variants:**
- `v0` — Bad deploy v2.4.1 with slow SQL query → connection pool exhaustion
- `v1` — Disk space exhaustion → PostgreSQL enters read-only mode

**Available `run_query` responses:**
```
"slow queries"    → 47.3s query from deploy v2.4.1
"recent deploy"   → v2.4.1 deployed 2h 7m ago
"connection pool" → 490/500 connections in use (98%)
"payment logs"    → FATAL: Could not acquire DB connection
"disk"            → /var/lib/postgresql at 99.1%
"wal"             → WAL archive lag 127 minutes
```

**Grading (5 criteria, total = 1.0):**

| Criterion | Weight |
|-----------|--------|
| Identify the slow query / disk issue | 0.20 |
| Link issue to root cause (deploy / disk) | 0.20 |
| Identify connection pool / read-only mode | 0.20 |
| Acknowledge correct root cause alert | 0.20 |
| Suggest correct fix | 0.20 |

---

### 📕 Task 3: Full Incident Runbook `full_incident_runbook` — Hard (20 steps max)

**The Scenario:** Company-wide login outage. Three services failing simultaneously. The cascade chain is deliberately non-obvious. Root cause: Redis `maxmemory-policy` set to `noeviction`.

**The Cascade Chain:**
```
Redis OOM (noeviction policy)
    ↓ cache writes rejected
Auth service retry storm → CPU 94%
    ↓ DB fallback also fails
Mobile API receives 503s from auth
    ↓ circuit breaker opens
100% of logins failing — SEV1 declared
```

**Three Red Herring Alerts** that waste agent steps:
- `WARNING: api-gateway connection pool at 75%` — not the cause
- `INFO: payment-service heap memory at 78%` — not the cause
- `WARNING: db-primary replication lag 2.3s` — not the cause

**Strict Fix Ordering Required:**
```
Step 1: Fix Redis (maxmemory-policy) ← must come first
Step 2: Restart auth-service         ← must come second
Step 3: Reset mobile-api circuit breaker ← must come third
Wrong order = no ordering reward
```

**Specific Technical Knowledge Required:**
Agent must know Redis configuration commands. Generic "fix redis" does not earn reward. Must use: `maxmemory-policy`, `allkeys-lru`, `CONFIG SET maxmemory`, etc.

**Complete Postmortem Required (4 sections):**

| Section | Keywords Required | Weight |
|---------|------------------|--------|
| Timeline | "timeline", "chronology" | 0.05 |
| Root Cause Analysis | "root cause", "rca" | 0.05 |
| Action Items | "action items", "follow-up", "remediation" | 0.05 |
| Prevention | "prevention", "prevent", "mitigation" | 0.05 |

**Grading (13 criteria, total = 1.0):**

| Criterion | Weight |
|-----------|--------|
| Triage redis as P1 root cause | 0.08 |
| Triage auth-service as P1 secondary | 0.08 |
| Diagnose Redis OOM as origin | 0.12 |
| Diagnose full cascade chain | 0.12 |
| Apply specific Redis config fix | 0.10 |
| Apply auth-service recovery | 0.08 |
| Apply mobile-api circuit breaker reset | 0.07 |
| Apply fixes in correct ORDER | 0.10 |
| Postmortem: timeline | 0.05 |
| Postmortem: root cause | 0.05 |
| Postmortem: action items | 0.05 |
| Postmortem: prevention | 0.05 |
| Never blamed wrong service | 0.05 |

**Penalty:** `-0.10` if agent applies fix to api-gateway or payment before diagnosing Redis OOM.

---

## 📊 Baseline Scores

### With Llama 3.3 70B (via Groq) — Zero-Shot

| Task | Steps Used | Final Score | Success |
|------|-----------|-------------|---------|
| `alert_triage` | 4 / 8 | **0.99** | ✅ |
| `root_cause_diagnosis` | 5 / 10 | **0.99** | ✅ |
| `full_incident_runbook` | 20 / 20 | **0.50** | ✅ |
| **Average** | **9.7** | **0.83** | **3/3** |

### With Qwen 2.5 72B (via HF Router) — Zero-Shot

| Task | Steps Used | Final Score | Success |
|------|-----------|-------------|---------|
| `alert_triage` | 5 / 8 | **1.00** | ✅ |
| `root_cause_diagnosis` | 4 / 10 | **1.00** | ✅ |
| `full_incident_runbook` | 6 / 20 | **0.41** | ✅ |
| **Average** | **5** | **0.80** | **3/3** |

> **Key observation:** The hard task (full_incident_runbook) genuinely challenges frontier models — Llama 70B scores 0.50 and Qwen 72B scores 0.41. Both fail to complete the postmortem and get confused by red herring alerts. This is by design.

---

## 🌟 Key Design Decisions

### 1. Fuzzy Grading — Never Require Exact Strings

```python
def matches_any(text: str, keywords: List[str]) -> bool:
    """Case-insensitive substring matching — generous by design."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)

# "db cpu is really high" → matches ["db-primary", "cpu", "database"]
# "DATABASE OVERLOAD"     → matches (case insensitive)  
# "connection exhausted"  → matches ["connection pool", "pool"]
```

### 2. Thread-Safe Session Management

```python
# Each /reset creates a completely isolated session
# Up to 50 concurrent sessions supported
# Oldest sessions auto-evicted (FIFO)
sessions: OrderedDict[str, SREEnvironment] = OrderedDict()
MAX_SESSIONS = 50

# Session ID returned in response header AND body
response.headers["X-Session-ID"] = session_id
observation.session_id = session_id
```

### 3. Red Herrings For Realistic Difficulty

Task 3 deliberately includes misleading alerts that look important but aren't. This tests whether agents can resist the urge to investigate irrelevant signals — a critical real-world SRE skill.

### 4. Strict Fix Ordering

Real incident response has dependencies. Restarting auth before fixing Redis won't work — auth will just crash again immediately. The ordering criterion tests whether agents understand *why* fixes must happen in sequence.

### 5. Scenario Variants For Replayability

Each task has multiple scenario variants selected randomly on reset. This prevents agents from memorizing answers and ensures scores reflect genuine reasoning ability.

### 6. Comprehensive Test Suite

```bash
pytest tests/ -v --tb=short
# 29 passed in 0.25s
```

Every grader criterion is independently tested. Fuzzy matching, penalty logic, fix ordering, postmortem completeness, session isolation — all verified.

---

## 💰 Reward Function

**Cumulative and partial — never binary.**

```
reset()  → reward = 0.00
step 1   → reward = 0.15  (acknowledged root cause)
step 2   → reward = 0.30  (classified P1)
step 3   → reward = 0.45  (diagnosed root cause)
step 4   → reward = 0.70  (classified remaining alerts)
step 5   → reward = 0.85  (identified cascade)
step 6   → reward = 0.99  (complete) → done=True
```

**Penalties:**
```
-0.10  Apply fix to wrong service before root cause identified
-0.05  Escalate when reward already > 0.5 (unnecessary escalation)
-0.05  Blame wrong service as root cause (Task 3)
-0.02  Noop after step 5 (penalizes stalling)
 0.00  Minimum floor — reward never goes negative
```

**Episode ends when:** reward ≥ 0.95 OR max_steps reached

---

## 🔌 Full API Reference

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

Returns `ObservationModel` + `X-Session-ID` response header

### `POST /step`
```bash
curl -X POST /step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "diagnose", "value": "db-primary CPU overload root cause"}'
```

Returns `StepResultModel` with `reward`, `done`, `success`, `info.grader_breakdown`

### `GET /state`
Returns current task, episode ID, step count, cumulative reward, per-criterion grader scores

### `GET /tasks`
Returns all 3 task definitions with difficulty, max_steps, description

### `GET /docs`
Interactive Swagger UI for all endpoints

---

## 📁 Project Structure

```
sre-incident-response/
│
├── main.py                  ← FastAPI app — all 7 endpoints, session management
├── environment.py           ← SREEnvironment — loop detection, state management
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
│                               Red herrings, strict ordering, 4-section postmortem
│
├── graders/
│   ├── __init__.py
│   └── base_grader.py       ← Fuzzy matching grader engine
│
├── data/
│   ├── __init__.py
│   └── scenarios.py         ← All scenario data + variants (random selection on reset)
│
├── server/
│   ├── __init__.py
│   └── app.py               ← OpenEnv server entry point
│
└── tests/
    ├── __init__.py
    ├── conftest.py           ← Pytest fixtures
    └── test_graders.py      ← 29 tests covering all graders
        ├── TestAlertTriageGrader      (10 tests)
        ├── TestRootCauseDiagnosisGrader (5 tests)
        ├── TestFullRunbookGrader       (7 tests)
        └── TestEnvironmentCore         (7 tests)
```

---

## 🚀 Setup & Installation

### Local (pip)

```bash
git clone https://github.com/KartikAneja5/sre-incident-response.git
cd sre-incident-response

pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000

curl http://localhost:8000/health
```

### Docker

```bash
docker build -t sre-env .

docker run -p 8000:7860 sre-env

curl http://localhost:8000/health
# {"status":"ok","environment":"sre-incident-response","version":"1.0.0"}
```

### HuggingFace Space (Live)

```bash
curl https://kartikaneja5-sre-incident-response.hf.space/health
```

---

## 🧪 Running Tests

```bash
pip install pytest
pytest tests/ -v --tb=short

# Expected output:
# 29 passed in 0.25s
```

Tests cover: partial rewards, fuzzy matching, fix ordering, postmortem completeness, session isolation, scenario variants, penalty logic, episode boundaries.

---

## 🤖 Running the Baseline

```bash
# With HuggingFace router
export HF_TOKEN=your_hf_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_BASE_URL=http://localhost:8000

python inference.py
```

**Expected stdout:**
```
[START] task=alert_triage env=sre-incident-response model=Qwen/Qwen2.5-72B-Instruct
[STEP]  step=1 action=acknowledge_alert('CRITICAL: db-primary CPU > 95%') reward=0.30 done=false error=null
[STEP]  step=2 action=diagnose('db-primary CPU overload cascading failures') reward=0.45 done=false error=null
[STEP]  step=3 action=diagnose('payment-service P1 downstream') reward=0.70 done=false error=null
[STEP]  step=4 action=diagnose('cascade from db to all services') reward=0.99 done=true error=null
[END]   success=true steps=4 score=0.99 rewards=0.30,0.45,0.70,0.99
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `https://router.huggingface.co/v1` | LLM API endpoint |
| `MODEL_NAME` | `Qwen/Qwen2.5-72B-Instruct` | Model identifier |
| `HF_TOKEN` | — | API key |
| `ENV_BASE_URL` | `http://localhost:8000` | Environment server URL |

---

## ✅ OpenEnv Spec Compliance

```bash
$ openenv validate
[OK] sre-incident-response: Ready for multi-mode deployment
```

| Requirement | Status |
|-------------|--------|
| Typed Pydantic v2 models | ✅ |
| `POST /reset` → `ObservationModel` | ✅ |
| `POST /step` → `StepResultModel` | ✅ |
| `GET /state` → `StateModel` | ✅ |
| `openenv.yaml` valid | ✅ |
| `pyproject.toml` with server entry point | ✅ |
| `uv.lock` present | ✅ |
| 3+ tasks with graders | ✅ |
| Scores strictly in `[0.0, 1.0]` | ✅ |
| Docker builds cleanly | ✅ |
| HF Space live and responding | ✅ |
| 29 passing tests | ✅ |
| Thread-safe session management | ✅ |

---

## 🧠 Why Frontier Models Struggle With Task 3

| Challenge | Why It's Hard |
|-----------|---------------|
| **3 red herring alerts** | Models waste steps on api-gateway and payment-service |
| **Specific technical knowledge** | Must know `maxmemory-policy allkeys-lru` — generic answers fail |
| **Strict fix ordering** | Fixing auth before Redis causes auth to immediately fail again |
| **4-section postmortem** | Must include timeline + RCA + action items + prevention |
| **Cascade reasoning** | Must trace Redis OOM → auth retry storm → circuit breaker → login outage |
| **Wrong service penalty** | Blaming wrong service costs -0.10 reward |

Even GPT-4 class models typically score 0.40-0.65 on this task — making it genuinely valuable for evaluation.

---

## 📄 License

MIT — Built by [Kartik Aneja](https://github.com/KartikAneja5) and [Nihal Joshi](https://github.com/Nihal040806) for the Meta × Hugging Face OpenEnv Hackathon 2026