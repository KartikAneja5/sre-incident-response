"""
All synthetic scenario data for the SRE Incident Response environment.
Contains logs, metrics, alerts, and metadata for all 3 tasks.
"""

from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════
# TASK 1: Alert Triage — 5 cascading alerts from db-primary CPU
# ═══════════════════════════════════════════════════════════

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

ALERT_TRIAGE_GOAL: str = (
    "You are an on-call SRE engineer. 5 alerts are firing simultaneously across your microservices stack. "
    "You must: (1) Acknowledge the most critical alert first, (2) Classify each alert by priority "
    "(P1/P2/P3), (3) Identify the root cause alert and explain why, (4) Explain the cascading failure pattern."
)

ALERT_TRIAGE_HINT: str = (
    "Hint: Look at which service's failure could cause all other alerts to fire. "
    "Check the database metrics carefully."
)


# ═══════════════════════════════════════════════════════════
# TASK 2: Root Cause Diagnosis — Bad deploy + slow query chain
# ═══════════════════════════════════════════════════════════

ROOT_CAUSE_LOGS: List[str] = [
    "[2026-04-10 01:23:00 UTC] [deploy-system] INFO: Deployed payment-service v2.4.1 at 01:23:00 UTC",
    "[2026-04-10 01:23:01 UTC] [deploy-system] INFO: Previous version: v2.4.0 — rollback available",
    "[2026-04-10 01:25:14 UTC] [db-primary] SLOW QUERY: SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id WHERE orders.status IN ('pending','processing') ORDER BY created_at DESC — execution time: 47.3s [introduced in deploy v2.4.1]",
    "[2026-04-10 01:30:22 UTC] [db-primary] WARN: Connection pool at 98% capacity (490/500 connections in use)",
    "[2026-04-10 01:30:45 UTC] [db-primary] WARN: 847 queries waiting in queue — pool saturation imminent",
    "[2026-04-10 01:31:03 UTC] [payment-service] FATAL: Could not acquire DB connection from pool (timeout=30s)",
    "[2026-04-10 01:31:15 UTC] [payment-service] ERROR: Transaction processing failed — no DB connection available",
    "[2026-04-10 01:31:30 UTC] [payment-service] ERROR: Retrying request 1/3... upstream DB not responding",
    "[2026-04-10 01:31:45 UTC] [payment-service] ERROR: Retrying request 2/3... upstream DB not responding",
    "[2026-04-10 01:32:00 UTC] [payment-service] ERROR: Retrying request 3/3... giving up — returning HTTP 503",
]

ROOT_CAUSE_METRICS: Dict[str, float] = {
    "payment_success_rate": 0.0,
    "db_connection_pool_usage": 98.0,
    "db_slow_query_count": 847.0,
    "payment_latency_p99_ms": 47300.0,
    "deploy_age_minutes": 127.0,
    "db_queue_depth": 847.0,
}

ROOT_CAUSE_ALERTS: List[str] = [
    "CRITICAL: payment-service returning HTTP 503 — 0% success rate",
    "CRITICAL: db-primary connection pool > 95% — pool exhaustion imminent",
    "WARNING: db-primary slow query count exceeding threshold",
    "WARNING: payment-service latency p99 > 40s",
    "INFO: Recent deployment — payment-service v2.4.1 deployed 2h 7m ago",
]

ROOT_CAUSE_GOAL: str = (
    "Payment service is completely down (HTTP 503). The incident started approximately 2 hours ago. "
    "You must: (1) Investigate the root cause by querying logs, (2) Identify the bad deployment, "
    "(3) Trace the failure chain from deploy → slow query → pool exhaustion → 503, "
    "(4) Recommend and apply the correct fix."
)

ROOT_CAUSE_HINT: str = (
    "Hint: Check what changed recently. Use run_query to investigate slow queries, "
    "recent deployments, and connection pool status."
)

# Sub-query results for run_query action in Task 2
ROOT_CAUSE_QUERY_RESULTS: Dict[str, List[str]] = {
    "slow_queries": [
        "[2026-04-10 01:25:14 UTC] [db-primary] SLOW QUERY: SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id WHERE orders.status IN ('pending','processing') ORDER BY created_at DESC — execution time: 47.3s [introduced in deploy v2.4.1]",
        "[2026-04-10 01:27:33 UTC] [db-primary] SLOW QUERY: Same query pattern repeated — 45.1s",
        "[2026-04-10 01:29:52 UTC] [db-primary] SLOW QUERY: Same query pattern repeated — 49.8s",
        "[db-primary] Total slow queries in last 2h: 847 — all from the same query pattern",
    ],
    "deploy": [
        "[2026-04-10 01:23:00 UTC] [deploy-system] INFO: Deployed payment-service v2.4.1 at 01:23:00 UTC",
        "[2026-04-10 01:23:01 UTC] [deploy-system] INFO: Previous version: v2.4.0 — rollback available",
        "[deploy-system] Changelog v2.4.1: Updated order listing query to include customer join for new dashboard feature",
        "[deploy-system] v2.4.1 deployed by: ci-pipeline (auto-merge PR #1847)",
    ],
    "connection_pool": [
        "[2026-04-10 01:30:22 UTC] [db-primary] WARN: Connection pool at 98% capacity (490/500)",
        "[2026-04-10 01:30:45 UTC] [db-primary] WARN: 847 queries waiting in queue",
        "[db-primary] Pool config: max_connections=500, timeout=30s, idle_timeout=300s",
        "[db-primary] Active connections breakdown: 485 from payment-service, 3 from auth-service, 2 from admin",
    ],
    "payment": [
        "[2026-04-10 01:31:03 UTC] [payment-service] FATAL: Could not acquire DB connection from pool (timeout=30s)",
        "[2026-04-10 01:31:15 UTC] [payment-service] ERROR: Transaction processing failed — no DB connection available",
        "[2026-04-10 01:31:30 UTC] [payment-service] ERROR: Retrying request 1/3... upstream DB not responding",
        "[2026-04-10 01:32:00 UTC] [payment-service] ERROR: Retrying request 3/3... giving up — returning HTTP 503",
        "[payment-service] Total failed requests in last 2h: 23,847",
    ],
}

# Keywords that map to query result keys for fuzzy matching
ROOT_CAUSE_QUERY_KEYWORDS: Dict[str, List[str]] = {
    "slow_queries": ["slow query", "slow queries", "slow sql", "query time", "long query", "query performance"],
    "deploy": ["deploy", "deployment", "recent deploy", "release", "version", "v2.4", "changelog", "what changed"],
    "connection_pool": ["connection pool", "connections", "pool", "db connections", "pool usage", "pool exhaustion"],
    "payment": ["payment logs", "payment errors", "payment service", "payment", "503", "payment-service"],
}


# ═══════════════════════════════════════════════════════════
# TASK 3: Full Incident Runbook — Redis OOM cascade
# ═══════════════════════════════════════════════════════════

FULL_RUNBOOK_LOGS: List[str] = [
    "[2026-04-10 02:00:01 UTC] [redis] CRITICAL: OOM command not allowed when used memory > maxmemory (policy: noeviction)",
    "[2026-04-10 02:00:03 UTC] [redis] WARN: Memory usage 99.8% (3.99GB/4.00GB) — maxmemory-policy: noeviction",
    "[2026-04-10 02:00:05 UTC] [redis] ERROR: Rejected SET command — out of memory",
    "[2026-04-10 02:00:10 UTC] [auth-service] ERROR: Failed to write session to cache: OOM — Redis rejected write",
    "[2026-04-10 02:00:12 UTC] [auth-service] WARN: Cache write failed, falling back to DB (attempt 1/3)",
    "[2026-04-10 02:00:15 UTC] [auth-service] WARN: Cache write failed, falling back to DB (attempt 2/3)",
    "[2026-04-10 02:00:18 UTC] [auth-service] ERROR: Cache write failed, falling back to DB (attempt 3/3) — giving up",
    "[2026-04-10 02:00:25 UTC] [auth-service] WARN: CPU at 94% — retry storm detected, thread pool saturated",
    "[2026-04-10 02:00:30 UTC] [auth-service] ERROR: DB fallback also failing — connection refused (pool exhausted)",
    "[2026-04-10 02:00:35 UTC] [auth-service] FATAL: Cannot validate tokens — all backends unavailable",
    "[2026-04-10 02:00:40 UTC] [mobile-api] ERROR: Auth service returned 503 for /validate-token",
    "[2026-04-10 02:00:45 UTC] [mobile-api] WARN: Auth service failure rate at 100% — triggering circuit breaker",
    "[2026-04-10 02:00:48 UTC] [mobile-api] ERROR: Circuit breaker OPENED for auth-service — all requests short-circuited",
    "[2026-04-10 02:00:50 UTC] [mobile-api] CRITICAL: 100% of login requests failing — users cannot authenticate",
    "[2026-04-10 02:01:00 UTC] [monitoring] ALERT: Company-wide login success rate dropped to 0% — SEV1 incident declared",
]

FULL_RUNBOOK_METRICS: Dict[str, float] = {
    "redis_memory_usage_percent": 99.8,
    "auth_cpu_percent": 94.0,
    "auth_cache_hit_rate": 0.0,
    "mobile_api_error_rate": 100.0,
    "mobile_login_success_rate": 0.0,
    "redis_rejected_commands": 15847.0,
    "auth_db_connections": 498.0,
    "circuit_breaker_status": 1.0,
}

FULL_RUNBOOK_ALERTS: List[str] = [
    "CRITICAL: mobile-api login success rate = 0% — complete login outage",
    "CRITICAL: auth-service CPU > 90% — retry storm causing CPU saturation",
    "CRITICAL: redis memory > 99% — OOM rejecting all write commands",
    "WARNING: auth-service cache hit rate = 0% — all cache lookups failing",
    "WARNING: mobile-api circuit breaker OPEN — auth-service calls blocked",
    "WARNING: auth-service DB connection spike — 498/500 connections in use",
    "INFO: redis rejected commands spike — 15,847 rejected in last hour",
    "INFO: auth-service retry rate elevated — exponential backoff exhausted",
]

FULL_RUNBOOK_GOAL: str = (
    "Three cascading failures are happening simultaneously. Users cannot log in company-wide. "
    "You must: (1) Triage all 8 alerts and identify the root cause, (2) Diagnose the full cascade chain "
    "(Redis OOM → auth cache miss storm → auth CPU spike → mobile API circuit breaker), "
    "(3) Apply fixes IN THE CORRECT ORDER (Redis first, then auth, then mobile-api), "
    "(4) Write a postmortem with timeline, root cause analysis, and action items."
)

FULL_RUNBOOK_HINT: str = (
    "Hint: The cascade starts at the infrastructure layer. Which service's failure "
    "would cause all downstream services to fail? Check memory metrics."
)

# Sub-query results for run_query action in Task 3
FULL_RUNBOOK_QUERY_RESULTS: Dict[str, List[str]] = {
    "redis": [
        "[redis] Current memory: 3.99GB / 4.00GB (99.8%)",
        "[redis] maxmemory-policy: noeviction (PROBLEM: should be allkeys-lru or volatile-lru)",
        "[redis] Rejected commands in last hour: 15,847",
        "[redis] Connected clients: 247 (auth-service: 200, mobile-api: 30, other: 17)",
        "[redis] Key count: 4,231,847 — many expired keys not evicted due to noeviction policy",
    ],
    "auth": [
        "[auth-service] CPU: 94% — primarily retry loops for failed cache writes",
        "[auth-service] Cache hit rate: 0% — all reads returning miss, all writes rejected by Redis",
        "[auth-service] DB connection pool: 498/500 — fallback to DB is also saturated",
        "[auth-service] Thread pool: 198/200 threads active — most blocked on retries",
        "[auth-service] Error rate: 100% — no requests succeeding",
    ],
    "mobile": [
        "[mobile-api] Circuit breaker status: OPEN for auth-service",
        "[mobile-api] Login success rate: 0%",
        "[mobile-api] Error rate: 100% — all requests failing at auth validation step",
        "[mobile-api] Affected users (estimated): 47,000 concurrent",
    ],
    "circuit_breaker": [
        "[mobile-api] Circuit breaker configuration: threshold=50% failures over 60s window",
        "[mobile-api] Circuit breaker opened at 02:00:48 UTC",
        "[mobile-api] Circuit breaker will attempt half-open at 02:05:48 UTC (5min cooldown)",
        "[mobile-api] To manually reset: restart mobile-api pods or call /admin/circuit-breaker/reset",
    ],
    "memory": [
        "[redis] Memory breakdown: session_tokens=2.1GB, user_profiles=1.2GB, rate_limits=0.5GB, other=0.19GB",
        "[redis] Peak memory in last 24h: 4.00GB (hit limit at 01:58:00 UTC)",
        "[redis] Memory growth rate: ~50MB/hour (session tokens not expiring properly)",
        "[redis] Recommendation: Set maxmemory-policy to allkeys-lru and increase maxmemory to 8GB",
    ],
}

FULL_RUNBOOK_QUERY_KEYWORDS: Dict[str, List[str]] = {
    "redis": ["redis", "cache", "redis memory", "redis config", "redis status", "oom"],
    "auth": ["auth", "auth-service", "authentication", "auth service", "auth logs", "auth errors"],
    "mobile": ["mobile", "mobile-api", "mobile api", "login", "mobile logs"],
    "circuit_breaker": ["circuit breaker", "circuit-breaker", "breaker", "cb status"],
    "memory": ["memory", "mem", "memory usage", "memory breakdown", "redis mem"],
}


def get_scenario_data(task_id: str) -> Dict[str, Any]:
    """Get the complete scenario data for a given task ID."""
    scenarios = {
        "alert_triage": {
            "logs": ALERT_TRIAGE_LOGS,
            "metrics": ALERT_TRIAGE_METRICS,
            "alerts": ALERT_TRIAGE_ALERTS,
            "goal": ALERT_TRIAGE_GOAL,
            "hint": ALERT_TRIAGE_HINT,
            "max_steps": 8,
            "name": "Alert Triage — Cascading Failures from DB CPU Overload",
            "difficulty": "easy",
        },
        "root_cause_diagnosis": {
            "logs": ROOT_CAUSE_LOGS,
            "metrics": ROOT_CAUSE_METRICS,
            "alerts": ROOT_CAUSE_ALERTS,
            "goal": ROOT_CAUSE_GOAL,
            "hint": ROOT_CAUSE_HINT,
            "max_steps": 10,
            "name": "Root Cause Diagnosis — Bad Deploy and Slow Query",
            "difficulty": "medium",
            "query_results": ROOT_CAUSE_QUERY_RESULTS,
            "query_keywords": ROOT_CAUSE_QUERY_KEYWORDS,
        },
        "full_incident_runbook": {
            "logs": FULL_RUNBOOK_LOGS,
            "metrics": FULL_RUNBOOK_METRICS,
            "alerts": FULL_RUNBOOK_ALERTS,
            "goal": FULL_RUNBOOK_GOAL,
            "hint": FULL_RUNBOOK_HINT,
            "max_steps": 15,
            "name": "Full Incident Runbook — Redis OOM Cascade to Login Outage",
            "difficulty": "hard",
            "query_results": FULL_RUNBOOK_QUERY_RESULTS,
            "query_keywords": FULL_RUNBOOK_QUERY_KEYWORDS,
        },
    }
    return scenarios.get(task_id, {})


def get_all_task_info() -> List[Dict[str, str]]:
    """Return metadata for all available tasks."""
    return [
        {
            "id": "alert_triage",
            "name": "Alert Triage",
            "difficulty": "easy",
            "max_steps": 8,
            "description": "Classify 5 simultaneous alerts and identify the root cause alert",
        },
        {
            "id": "root_cause_diagnosis",
            "name": "Root Cause Diagnosis",
            "difficulty": "medium",
            "max_steps": 10,
            "description": "Diagnose a payment service outage caused by a bad deploy and slow query",
        },
        {
            "id": "full_incident_runbook",
            "name": "Full Incident Runbook",
            "difficulty": "hard",
            "max_steps": 15,
            "description": "Handle a 3-service cascade failure from Redis OOM to mobile login outage",
        },
    ]
