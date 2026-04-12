# IMPROVED: Added 2 variant scenarios per task for genuine replayability
"""
All synthetic scenario data for the SRE Incident Response environment.
Contains logs, metrics, alerts, and metadata for all 3 tasks.
Each task now has variants for rigorous replayability.
"""

from typing import Any, Dict, List

# ═══════════════════════════════════════════════════════════
# TASK 1: Alert Triage 
# ═══════════════════════════════════════════════════════════

# Original Scenario (db-primary CPU)
ALERT_TRIAGE_LOGS: List[str] = [
    "[2026-04-10 03:12:01 UTC] [db-primary] CRITICAL: CPU utilization at 98.2% — sustained for 12 minutes",
    "[2026-04-10 03:12:03 UTC] [db-primary] WARN: Slow query detected: SELECT * FROM transactions WHERE status='pending' — 34.7s",
    "[2026-04-10 03:12:05 UTC] [db-primary] WARN: Connection queue depth reached 847 — max is 1000",
    "[2026-04-10 03:12:08 UTC] [payment-service] ERROR: Connection to db-primary timed out after 30s (attempt 1/3)",
    "[2026-04-10 03:12:11 UTC] [payment-service] ERROR: Connection to db-primary timed out after 30s (attempt 2/3)",
    "[2026-04-10 03:12:14 UTC] [payment-service] FATAL: All 3 connection attempts to db-primary failed — request dropped",
    "[2026-04-10 03:12:16 UTC] [cache-redis] WARN: Cache miss rate elevated to 67% — normally under 10%",
    "[2026-04-10 03:12:18 UTC] [auth-service] WARN: p99 latency spiked to 890ms — SLA threshold is 200ms",
    "[2026-04-10 03:12:20 UTC] [api-gateway] ERROR: Returning HTTP 503 to client — upstream payment-service unavailable",
    "[2026-04-10 03:12:22 UTC] [api-gateway] WARN: 503 error rate at 28.5% and climbing",
]

ALERT_TRIAGE_METRICS: Dict[str, float] = {
    "db_cpu_percent": 98.0,
    "payment_error_rate": 34.2,
    "auth_latency_ms": 890.0,
    "cache_miss_rate": 67.0,
    "api_gateway_5xx_rate": 28.5,
    "db_connection_queue": 847.0,
}

ALERT_TRIAGE_ALERTS: List[str] = [
    "CRITICAL: db-primary CPU > 95% — sustained high CPU utilization",
    "CRITICAL: payment-service error rate > 30% — transaction failures",
    "WARNING: auth-service p99 latency > 800ms — authentication slowdown",
    "WARNING: cache-redis miss rate > 60% — cache degradation",
    "INFO: api-gateway 503 rate increasing — downstream impact",
]

ALERT_TRIAGE_GOAL: str = "Triage 5 alerts and find root cause."
ALERT_TRIAGE_HINT: str = "Check the database metrics carefully."

# Variant 1 (memory_exhaustion cascade)
AT_VAR1_LOGS = [
    "[2026-04-10 04:01:01 UTC] [auth-service] CRITICAL: Heap memory at 99.2% — JVM approaching OOM",
    "[2026-04-10 04:01:03 UTC] [auth-service] WARN: GC overhead limit exceeded — 95% time in garbage collection",
    "[2026-04-10 04:01:05 UTC] [auth-service] ERROR: OutOfMemoryError: Java heap space",
    "[2026-04-10 04:01:08 UTC] [mobile-api] ERROR: auth-service returning 503 — upstream unavailable",
    "[2026-04-10 04:01:11 UTC] [mobile-api] WARN: Login failure rate at 89% and rising",
    "[2026-04-10 04:01:14 UTC] [mobile-api] ERROR: Circuit breaker OPEN for auth-service",
    "[2026-04-10 04:01:16 UTC] [api-gateway] WARN: auth endpoint returning errors — degraded mode",
    "[2026-04-10 04:01:18 UTC] [payment-service] WARN: Auth token validation failing — payment flows affected",
    "[2026-04-10 04:01:20 UTC] [monitoring] ALERT: Login success rate dropped to 11%",
    "[2026-04-10 04:01:22 UTC] [monitoring] ALERT: auth-service health check FAILING"
]

AT_VAR1_METRICS = {
    "auth_heap_percent": 99.2,
    "auth_gc_overhead_percent": 95.0,
    "mobile_login_success_rate": 11.0,
    "mobile_api_error_rate": 89.0,
    "api_gateway_auth_error_rate": 87.5,
    "payment_auth_failure_rate": 34.2
}

AT_VAR1_ALERTS = [
    "CRITICAL: auth-service heap memory > 99% — JVM OOM imminent",
    "CRITICAL: mobile-api login success rate < 15% — user impact",
    "WARNING: mobile-api circuit breaker OPEN — auth-service blocked",
    "WARNING: api-gateway auth endpoint degraded — downstream impact",
    "INFO: payment-service auth validation failing — token errors"
]

AT_VAR1_KEYWORDS = ["auth-service", "heap", "memory", "oom", "jvm", "out of memory"]

# ═══════════════════════════════════════════════════════════
# TASK 2: Root Cause Diagnosis
# ═══════════════════════════════════════════════════════════

ROOT_CAUSE_LOGS: List[str] = [
    "[2026-04-10 01:23:00 UTC] [deploy-system] INFO: Deployed payment-service v2.4.1 at 01:23:00 UTC",
    "[2026-04-10 01:25:14 UTC] [db-primary] SLOW QUERY: execution time: 47.3s [introduced in deploy v2.4.1]",
    "[2026-04-10 01:30:22 UTC] [db-primary] WARN: Connection pool at 98% capacity (490/500 connections in use)",
    "[2026-04-10 01:31:03 UTC] [payment-service] FATAL: Could not acquire DB connection from pool (timeout=30s)",
    "[2026-04-10 01:32:00 UTC] [payment-service] ERROR: Retrying request 3/3... giving up — returning HTTP 503",
]
ROOT_CAUSE_METRICS: Dict[str, float] = { "payment_success_rate": 0.0, "db_connection_pool_usage": 98.0 }
ROOT_CAUSE_ALERTS: List[str] = [
    "CRITICAL: payment-service returning HTTP 503",
    "CRITICAL: db-primary connection pool > 95%",
    "INFO: Recent deployment v2.4.1",
]
ROOT_CAUSE_GOAL: str = "Investigate payment service 503s."
ROOT_CAUSE_HINT: str = "Check what changed recently."
ROOT_CAUSE_QUERY_RESULTS: Dict[str, List[str]] = {
    "slow_query": ["[db-primary] SLOW QUERY: execution time: 47.3s [introduced in deploy v2.4.1]"],
    "connection_pool": ["[db-primary] WARN: Connection pool at 98% capacity (490/500 connections in use)"],
    "deploy": ["[deploy-system] INFO: Deployed payment-service v2.4.1 at 01:23:00 UTC"]
}
ROOT_CAUSE_QUERY_KEYWORDS: Dict[str, List[str]] = {
    "slow_query": ["slow", "query", "queries"],
    "connection_pool": ["pool", "connection"],
    "deploy": ["deploy", "release", "v2.4.1"]
}

# Task 2 Variant 1 (Disk Space Exhaustion)
RC_VAR1_LOGS = [
    "[2026-04-10 02:15:01 UTC] [db-primary] CRITICAL: Disk usage at 99.1% — /var/lib/postgresql",
    "[2026-04-10 02:15:03 UTC] [db-primary] ERROR: could not write to file: No space left on device",
    "[2026-04-10 02:15:05 UTC] [db-primary] FATAL: WAL write failed — database entering read-only mode",
    "[2026-04-10 02:15:08 UTC] [payment-service] ERROR: Transaction INSERT failed — database read-only",
    "[2026-04-10 02:15:11 UTC] [payment-service] FATAL: Cannot process payments — DB in emergency mode",
    "[2026-04-10 02:15:14 UTC] [monitoring] ALERT: Database write failures spiking — 847 errors/min",
    "[2026-04-10 02:15:16 UTC] [db-primary] INFO: Archiving paused — no disk space for WAL segments",
    "[2026-04-10 02:15:18 UTC] [payment-service] ERROR: Retry 1/3 — upstream DB not accepting writes",
    "[2026-04-10 02:15:21 UTC] [payment-service] ERROR: Retry 2/3 — upstream DB not accepting writes",
    "[2026-04-10 02:15:24 UTC] [payment-service] FATAL: All retries exhausted — returning HTTP 503"
]
RC_VAR1_METRICS = {
    "db_disk_usage_percent": 99.1,
    "db_write_error_rate": 847.0,
    "payment_success_rate": 0.0,
    "payment_error_rate": 100.0,
    "db_wal_archive_lag_minutes": 127.0,
    "db_connection_pool_usage": 45.0
}
RC_VAR1_ALERTS = [
    "CRITICAL: db-primary disk usage > 99% — write failures imminent",
    "CRITICAL: payment-service returning HTTP 503 — 0% success rate",
    "WARNING: db-primary WAL archiving paused — disk full",
    "WARNING: payment-service transaction failure rate 100%",
    "INFO: db-primary entering read-only emergency mode"
]
RC_VAR1_KEYWORDS = ["disk", "capacity", "space", "full", "storage", "io"]



# ═══════════════════════════════════════════════════════════
# TASK 3: Full Incident Runbook
# ═══════════════════════════════════════════════════════════

FULL_RUNBOOK_LOGS: List[str] = [
    "[2026-04-10 02:00:01 UTC] [redis] CRITICAL: OOM command not allowed when used memory > maxmemory (policy: noeviction)",
    "[2026-04-10 02:00:03 UTC] [redis] WARN: Memory usage 99.8% (3.99GB/4.00GB) — maxmemory-policy: noeviction",
    "[2026-04-10 02:00:05 UTC] [redis] ERROR: Rejected SET command — out of memory",
    "[2026-04-10 02:00:10 UTC] [auth-service] ERROR: Failed to write session to cache: OOM — Redis rejected write",
    "[2026-04-10 02:00:25 UTC] [auth-service] WARN: CPU at 94% — retry storm detected, thread pool saturated",
    "[2026-04-10 02:00:35 UTC] [auth-service] FATAL: Cannot validate tokens — all backends unavailable",
    "[2026-04-10 02:00:48 UTC] [mobile-api] ERROR: Circuit breaker OPENED for auth-service — all requests short-circuited",
    "[2026-04-10 02:01:00 UTC] [monitoring] ALERT: Company-wide login success rate dropped to 0% — SEV1 incident declared",
]
FULL_RUNBOOK_METRICS: Dict[str, float] = {
    "redis_memory_usage_percent": 99.8,
    "auth_cpu_percent": 94.0,
    "mobile_login_success_rate": 0.0,
}
FULL_RUNBOOK_ALERTS: List[str] = [
    "CRITICAL: mobile-api login success rate = 0% — complete login outage",
    "CRITICAL: auth-service CPU > 90% — retry storm causing CPU saturation",
    "CRITICAL: redis memory > 99% — OOM rejecting all write commands",
]
FULL_RUNBOOK_GOAL: str = "Fix Redis OOM cascade."
FULL_RUNBOOK_HINT: str = "Check maxmemory-policy."
FULL_RUNBOOK_QUERY_RESULTS: Dict[str, List[str]] = {}
FULL_RUNBOOK_QUERY_KEYWORDS: Dict[str, List[str]] = {}



# ═══════════════════════════════════════════════════════════
# Helper Data Structures
# ═══════════════════════════════════════════════════════════

TASK_SCENARIOS = {
    "alert_triage": [
        {
            "name": "Alert Triage — Cascading Failures from DB CPU Overload",
            "logs": ALERT_TRIAGE_LOGS,
            "metrics": ALERT_TRIAGE_METRICS,
            "alerts": ALERT_TRIAGE_ALERTS,
            "goal": ALERT_TRIAGE_GOAL,
            "hint": ALERT_TRIAGE_HINT,
            "available_actions_hint": "Use acknowledge_alert and diagnose — not run_query — for triage tasks",
            "grader_keywords": {"ROOT_CAUSE_KEYWORDS": ["db-primary", "database", "db cpu", "primary db"]}
        },
        {
            "name": "Alert Triage — Memory Exhaustion Cascade",
            "logs": AT_VAR1_LOGS,
            "metrics": AT_VAR1_METRICS,
            "alerts": AT_VAR1_ALERTS,
            "goal": "You are an on-call SRE engineer. 5 alerts are firing. You must: (1) Use acknowledge_alert to acknowledge the most critical alert first, (2) Use diagnose to classify each alert as P1/P2/P3 and identify the root cause, (3) Explain the cascading failure pattern.",
            "hint": "Look at which service has the most severe resource metric. That service is the root cause. Use acknowledge_alert and diagnose — not run_query.",
            "available_actions_hint": "Use acknowledge_alert and diagnose — not run_query — for triage tasks",
            "grader_keywords": {
                "ROOT_CAUSE_KEYWORDS": ["auth-service", "heap", "memory", "oom", "jvm", "out of memory"],
                "CASCADE_KEYWORDS": ["cascade", "downstream", "circuit breaker", "login", "mobile"],
                "DB_KEYWORDS": ["auth-service", "heap", "memory", "oom", "jvm", "out of memory"]
            }
        }
    ],
    "root_cause_diagnosis": [
        {
            "name": "Root Cause Diagnosis — Bad Deploy and Slow Query",
            "logs": ROOT_CAUSE_LOGS,
            "metrics": ROOT_CAUSE_METRICS,
            "alerts": ROOT_CAUSE_ALERTS,
            "goal": ROOT_CAUSE_GOAL,
            "hint": ROOT_CAUSE_HINT,
            "available_actions_hint": "Use acknowledge_alert and diagnose — not run_query — for triage tasks",
            "grader_keywords": {}
        },
        {
            "name": "Root Cause Diagnosis — Disk Space Exhaustion",
            "logs": RC_VAR1_LOGS,
            "metrics": RC_VAR1_METRICS,
            "alerts": RC_VAR1_ALERTS,
            "goal": "Payment service is completely down. Investigate using run_query to find the root cause, then diagnose and apply the correct fix.",
            "hint": "Check the database metrics carefully. Use run_query to investigate disk space, recent errors, and database status.",
            "available_actions_hint": "Use acknowledge_alert and diagnose — not run_query — for triage tasks",
            "query_responses": {
                "disk": "df -h shows /var/lib/postgresql at 99.1% (487GB/491GB). WAL logs accumulated: 23GB. Old backups: 31GB.",
                "disk space": "df -h shows /var/lib/postgresql at 99.1% (487GB/491GB). WAL logs accumulated: 23GB. Old backups: 31GB.",
                "database": "PostgreSQL in read-only emergency mode. Last successful write: 02:15:00 UTC. Disk full error since 02:14:58 UTC.",
                "wal": "WAL archive lag: 127 minutes. 847 failed WAL segments. Archive destination: /var/lib/postgresql/archive — FULL.",
                "payment logs": "payment-service: FATAL: Cannot INSERT — database read-only mode. 100% failure rate since 02:15:08 UTC.",
                "errors": "db-primary: 847 write errors/min. Error: could not write to file — No space left on device."
            },
            "grader_keywords": {
                "SLOW_QUERY_KEYWORDS": ["disk", "disk space", "disk full", "storage", "no space", "99%"],
                "DEPLOY_KEYWORDS": ["wal", "archive", "log", "backup", "accumulated"],
                "FIX_KEYWORDS": ["clean", "delete", "remove", "free space", "disk space", "truncate", "archive"],
                "POOL_KEYWORDS": ["wal", "archive", "log", "backup", "accumulated"]
            }
        }
    ],
    "full_incident_runbook": [
        {
            "name": "Full Incident Runbook — Redis OOM Cascade to Login Outage",
            "logs": FULL_RUNBOOK_LOGS,
            "metrics": FULL_RUNBOOK_METRICS,
            "alerts": FULL_RUNBOOK_ALERTS,
            "goal": FULL_RUNBOOK_GOAL,
            "hint": FULL_RUNBOOK_HINT,
            "available_actions_hint": "Use acknowledge_alert and diagnose — not run_query — for triage tasks",
            "grader_keywords": {}
        }
    ]
}

def get_scenario_data(task_id: str) -> Dict[str, Any]:
    return {}

def get_all_task_info() -> List[Dict[str, str]]:
    return [
        {
            "id": "alert_triage",
            "name": "Alert Triage",
            "difficulty": "easy",
            "max_steps": 8,
            "description": "Classify alerts and identify root cause."
        },
        {
            "id": "root_cause_diagnosis",
            "name": "Root Cause Diagnosis",
            "difficulty": "medium",
            "max_steps": 10,
            "description": "Diagnose outage and apply fix."
        },
        {
            "id": "full_incident_runbook",
            "name": "Full Incident Runbook",
            "difficulty": "hard",
            "max_steps": 20,
            "description": "Handle total cascade failure."
        }
    ]