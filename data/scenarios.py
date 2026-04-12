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

# Variant 1 (network_partition)
AT_VAR1_LOGS = [
    "CRITICAL: Connection refused to payment-service (attempt 1/3)",
    "CRITICAL: Connection refused to auth-service",
    "WARN: Network timeout to db-primary — 5000ms",
    "FATAL: All upstream connections failing — serving 503s",
    "WARN: No incoming requests for 3 minutes (isolated)",
    "ALERT: api-gateway health check failing since 03:45 UTC",
]

AT_VAR1_METRICS = {
  "api_gateway_error_rate": 98.5,
  "api_gateway_upstream_failures": 3,
  "payment_request_rate": 0.0,
  "auth_request_rate": 0.0,
  "db_cpu_percent": 12.0,
  "network_packet_loss_percent": 87.3
}

AT_VAR1_ALERTS = [
    "CRITICAL: api-gateway upstream failure rate 98.5% [ROOT CAUSE]",
    "CRITICAL: payment-service receiving 0 requests — isolated",
    "WARNING: auth-service receiving 0 requests — isolated",
    "WARNING: monitoring — db-primary unreachable from gateway",
    "INFO: All service request rates dropped simultaneously",
]

AT_VAR1_KEYWORDS = ["api-gateway", "network", "connectivity", "upstream"]

# Variant 2 (memory_exhaustion)
AT_VAR2_LOGS = [
    "CRITICAL: auth-service memory exhausted - OutOfMemoryError",
    "WARN: auth-service heap usage at 99.9%",
    "ERROR: api-gateway unable to validate tokens - upstream auth timeout",
    "ERROR: mobile-api authentication failures cascading",
    "FATAL: JVM crashed in auth-service container",
]

AT_VAR2_METRICS = {
    "auth_heap_percent": 99.9,
    "auth_gc_pause_ms": 15000.0,
    "api_gateway_error_rate": 45.0,
    "mobile_auth_failure_rate": 100.0,
}

AT_VAR2_ALERTS = [
    "CRITICAL: auth-service heap memory > 99%",
    "CRITICAL: mobile-api auth failure 100%",
    "WARNING: api-gateway downstream latency spike",
    "WARNING: auth-service GC pause time critical",
    "INFO: general API degradation",
]

AT_VAR2_KEYWORDS = ["auth-service", "memory", "oom", "heap", "leak"]

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

# Task 2 Variant 1
RC_VAR1_LOGS = [
    "INFO: Changed load-balancer timeout to 1s at 04:00 UTC",
    "ERROR: payment-service timeout (took 1.5s > 1s)",
    "ERROR: 504 Gateway Timeout downstream"
]
RC_VAR1_METRICS = { "lb_timeout_ms": 1000.0, "payment_latency": 1500.0 }
RC_VAR1_ALERTS = ["CRITICAL: load-balancer returning 504s", "WARN: all services reporting timeouts"]
RC_VAR1_KEYWORDS = ["load", "balancer", "timeout", "lb", "1s", "load-balancer"]

# Task 2 Variant 2
RC_VAR2_LOGS = [
    "CRITICAL: No space left on device - /var/lib/mysql",
    "ERROR: payment-service db write failed",
    "FATAL: Database in read-only mode to prevent corruption"
]
RC_VAR2_METRICS = { "db_disk_usage": 99.9, "write_success_rate": 0.0 }
RC_VAR2_ALERTS = ["CRITICAL: db-primary disk space full", "CRITICAL: payment-service write failures"]
RC_VAR2_KEYWORDS = ["disk", "capacity", "space", "full", "storage", "io"]


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

# Task 3 Variant 1
FR_VAR1_LOGS = [
    "CRITICAL: x509: certificate has expired or is not yet valid (auth-service)",
    "ERROR: SSL handshake failed - certificate expired",
    "WARN: mobile-api connection to auth failed",
    "FATAL: login outage company-wide due to cert expiration"
]
FR_VAR1_METRICS = { "cert_validity_days": -1.0, "auth_success_rate": 0.0 }
FR_VAR1_ALERTS = ["CRITICAL: auth-service TLS certificate expired", "CRITICAL: mobile login failure"]
FR_VAR1_KEYWORDS = ["cert", "certificate", "tls", "ssl", "expired", "expiry"]

# Task 3 Variant 2
FR_VAR2_LOGS = [
    "CRITICAL: AWS region us-east-1 outage affecting routing",
    "ERROR: dns resolution failed for auth-service.internal",
    "WARN: BGP route flap detected",
    "FATAL: All internal cross-service traffic dropped"
]
FR_VAR2_METRICS = { "dns_resolution_success": 0.0, "network_drops": 100.0 }
FR_VAR2_ALERTS = ["CRITICAL: AWS us-east-1 routing failure", "CRITICAL: DNS resolution failing globally"]
FR_VAR2_KEYWORDS = ["aws", "region", "outage", "dns", "bgp", "routing"]


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
            "grader_keywords": {"ROOT_CAUSE_KEYWORDS": ["db-primary", "database", "db cpu", "primary db"]}
        },
        {
            "name": "Alert Triage — Network Partition at API Gateway",
            "logs": AT_VAR1_LOGS,
            "metrics": AT_VAR1_METRICS,
            "alerts": AT_VAR1_ALERTS,
            "goal": "Triage network isolation alerts.",
            "hint": "Check upstream connectivity.",
            "grader_keywords": {"ROOT_CAUSE_KEYWORDS": AT_VAR1_KEYWORDS, "DB_KEYWORDS": AT_VAR1_KEYWORDS}
        },
        {
            "name": "Alert Triage — Auth Service Memory Leak",
            "logs": AT_VAR2_LOGS,
            "metrics": AT_VAR2_METRICS,
            "alerts": AT_VAR2_ALERTS,
            "goal": "Triage memory exhaustion.",
            "hint": "Check JVM metrics.",
            "grader_keywords": {"ROOT_CAUSE_KEYWORDS": AT_VAR2_KEYWORDS, "DB_KEYWORDS": AT_VAR2_KEYWORDS}
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
            "grader_keywords": {}
        },
        {
            "name": "Root Cause Diagnosis — Misconfigured Timeout",
            "logs": RC_VAR1_LOGS,
            "metrics": RC_VAR1_METRICS,
            "alerts": RC_VAR1_ALERTS,
            "goal": "Investigate gateway timeouts.",
            "hint": "Check LB config.",
            "grader_keywords": {"SLOW_QUERY_KEYWORDS": RC_VAR1_KEYWORDS, "DEPLOY_KEYWORDS": RC_VAR1_KEYWORDS, "POOL_KEYWORDS": RC_VAR1_KEYWORDS}
        },
        {
            "name": "Root Cause Diagnosis — Disk Space Exhaustion",
            "logs": RC_VAR2_LOGS,
            "metrics": RC_VAR2_METRICS,
            "alerts": RC_VAR2_ALERTS,
            "goal": "Investigate write failures.",
            "hint": "Check storage metrics.",
            "grader_keywords": {"SLOW_QUERY_KEYWORDS": RC_VAR2_KEYWORDS, "DEPLOY_KEYWORDS": RC_VAR2_KEYWORDS, "POOL_KEYWORDS": RC_VAR2_KEYWORDS}
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
            "grader_keywords": {}
        },
        {
            "name": "Full Incident Runbook — Certificate Expiry",
            "logs": FR_VAR1_LOGS,
            "metrics": FR_VAR1_METRICS,
            "alerts": FR_VAR1_ALERTS,
            "goal": "Fix expired TLS cert.",
            "hint": "Check SSL/TLS dates.",
            "grader_keywords": {"REDIS_KEYWORDS": FR_VAR1_KEYWORDS}
        },
        {
            "name": "Full Incident Runbook — AWS Routing Outage",
            "logs": FR_VAR2_LOGS,
            "metrics": FR_VAR2_METRICS,
            "alerts": FR_VAR2_ALERTS,
            "goal": "Fix DNS/BGP routing.",
            "hint": "Wait for upstream restabilization.",
            "grader_keywords": {"REDIS_KEYWORDS": FR_VAR2_KEYWORDS}
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