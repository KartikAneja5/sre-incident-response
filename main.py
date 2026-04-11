# FIXED: [CHANGE 1] Baseline scores HTML section, [CHANGE 2] Cached task list
# [FIX 1] Thread-safe sessions, [FIX 2] /health, [FIX 3] root JSON fallback,
#        [FIX 4] /metrics endpoint, [FIX 5] /reset returns session_id
"""
FastAPI application for the SRE Incident Response OpenEnv environment.
All endpoints are implemented per the OpenEnv specification.
"""

import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from environment import SREEnvironment
from models import (
    ActionModel,
    MetricsModel,
    ObservationModel,
    ResetRequest,
    StateModel,
    StepResultModel,
    TaskInfo,
)

app = FastAPI(
    title="SRE Incident Response — OpenEnv Environment",
    description=(
        "An OpenEnv environment where AI agents act as on-call SRE engineers. "
        "Agents must triage alerts, diagnose root causes, apply fixes, and write "
        "postmortems for realistic synthetic infrastructure incidents."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════
# Session Management — replaces the single global env instance
# ═══════════════════════════════════════════════════════════

sessions: OrderedDict[str, SREEnvironment] = OrderedDict()
MAX_SESSIONS = 50

# Module-level stats (reset when server restarts)
_stats: Dict[str, Any] = {
    "total_resets": 0,
    "total_steps": 0,
    "total_episodes_completed": 0,
    "rewards_history": [],  # last 100 final rewards
}


def get_or_create_session(session_id: Optional[str] = None) -> tuple:
    """Retrieve an existing session by ID, or return the most recent session."""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]
    # Return most recent session if exists
    if sessions:
        sid = next(reversed(sessions))
        return sid, sessions[sid]
    raise RuntimeError("No active session. Call /reset first.")


def create_session() -> tuple:
    """Create a new session with a unique ID and an SREEnvironment instance."""
    sid = str(uuid.uuid4())
    env = SREEnvironment()
    sessions[sid] = env
    # Cleanup old sessions
    while len(sessions) > MAX_SESSIONS:
        sessions.popitem(last=False)
    return sid, env


LANDING_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SRE Incident Response — OpenEnv Environment</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-card: rgba(17, 24, 39, 0.7);
    --border-color: rgba(255, 255, 255, 0.06);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-red: #ef4444;
    --accent-orange: #f97316;
    --accent-yellow: #eab308;
    --accent-green: #22c55e;
    --accent-blue: #3b82f6;
    --accent-purple: #a855f7;
    --gradient-main: linear-gradient(135deg, #ef4444 0%, #f97316 50%, #eab308 100%);
    --gradient-glow: radial-gradient(ellipse at 50% 0%, rgba(239, 68, 68, 0.15) 0%, transparent 60%);
  }

  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Animated background */
  body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: var(--gradient-glow);
    pointer-events: none;
    z-index: 0;
  }

  .container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 24px;
    position: relative;
    z-index: 1;
  }

  /* Header */
  .header {
    padding: 48px 0 24px;
    text-align: center;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 100px;
    font-size: 13px;
    font-weight: 500;
    color: #f87171;
    margin-bottom: 20px;
    animation: fadeIn 0.6s ease;
  }

  .badge .pulse {
    width: 8px; height: 8px;
    background: var(--accent-green);
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.3); }
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  h1 {
    font-size: clamp(2rem, 5vw, 3.2rem);
    font-weight: 800;
    background: var(--gradient-main);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin-bottom: 16px;
    animation: fadeIn 0.6s ease 0.1s both;
  }

  .subtitle {
    font-size: 17px;
    color: var(--text-secondary);
    max-width: 640px;
    margin: 0 auto 32px;
    line-height: 1.7;
    animation: fadeIn 0.6s ease 0.2s both;
  }

  .header-actions {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
    animation: fadeIn 0.6s ease 0.3s both;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.25s ease;
    cursor: pointer;
    border: none;
    font-family: inherit;
  }

  .btn-primary {
    background: var(--gradient-main);
    color: #fff;
    box-shadow: 0 4px 24px rgba(239, 68, 68, 0.25);
  }
  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(239, 68, 68, 0.35);
  }

  .btn-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    backdrop-filter: blur(12px);
  }
  .btn-secondary:hover {
    border-color: rgba(255,255,255,0.15);
    background: rgba(30, 41, 59, 0.8);
    transform: translateY(-2px);
  }

  /* Status bar */
  .status-bar {
    display: flex;
    gap: 24px;
    justify-content: center;
    flex-wrap: wrap;
    padding: 20px 0 40px;
    animation: fadeIn 0.6s ease 0.4s both;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-muted);
  }

  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
  }
  .status-dot.green { background: var(--accent-green); box-shadow: 0 0 8px rgba(34,197,94,0.5); }
  .status-dot.blue { background: var(--accent-blue); }
  .status-dot.purple { background: var(--accent-purple); }

  /* Section */
  .section {
    margin-bottom: 48px;
  }

  .section-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    margin-bottom: 20px;
    padding-left: 4px;
  }

  /* Task Cards */
  .tasks-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
  }

  .task-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 28px;
    backdrop-filter: blur(16px);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }
  .task-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 16px 16px 0 0;
  }
  .task-card:hover {
    border-color: rgba(255,255,255,0.1);
    transform: translateY(-4px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.3);
  }

  .task-card.easy::before { background: var(--accent-green); }
  .task-card.medium::before { background: var(--accent-yellow); }
  .task-card.hard::before { background: var(--accent-red); }

  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .task-name {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .difficulty-badge {
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .difficulty-badge.easy { background: rgba(34,197,94,0.12); color: #4ade80; }
  .difficulty-badge.medium { background: rgba(234,179,8,0.12); color: #facc15; }
  .difficulty-badge.hard { background: rgba(239,68,68,0.12); color: #f87171; }

  .task-desc {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: 16px;
  }

  .task-meta {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .task-meta span {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* API Endpoints */
  .endpoints-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 12px;
  }

  .endpoint-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 20px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    backdrop-filter: blur(12px);
    transition: all 0.25s ease;
  }
  .endpoint-card:hover {
    border-color: rgba(255,255,255,0.1);
    background: rgba(30,41,59,0.5);
  }

  .method {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.02em;
    flex-shrink: 0;
  }
  .method.get { background: rgba(34,197,94,0.12); color: #4ade80; }
  .method.post { background: rgba(59,130,246,0.12); color: #60a5fa; }

  .endpoint-path {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .endpoint-desc {
    font-size: 12px;
    color: var(--text-muted);
    margin-left: auto;
    text-align: right;
  }

  /* Action Types */
  .actions-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
    backdrop-filter: blur(12px);
  }

  .actions-table th {
    text-align: left;
    padding: 14px 20px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid var(--border-color);
  }

  .actions-table td {
    padding: 12px 20px;
    font-size: 13px;
    border-bottom: 1px solid var(--border-color);
  }
  .actions-table tr:last-child td { border-bottom: none; }

  .actions-table td:first-child {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    color: #f9a8d4;
    font-size: 13px;
  }
  .actions-table td:nth-child(2) { color: var(--text-secondary); }
  .actions-table td:nth-child(3) {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-muted);
  }

  /* Grading Section */
  .grading-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 16px;
  }

  .grading-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 24px;
    backdrop-filter: blur(12px);
  }

  .grading-card h4 {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .grading-card p {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
  }

  .reward-bar {
    height: 4px;
    background: rgba(255,255,255,0.05);
    border-radius: 4px;
    margin-top: 12px;
    overflow: hidden;
  }

  .reward-fill {
    height: 100%;
    border-radius: 4px;
    background: var(--gradient-main);
    transition: width 1s ease;
  }

  /* Footer */
  .footer {
    text-align: center;
    padding: 40px 0;
    color: var(--text-muted);
    font-size: 13px;
    border-top: 1px solid var(--border-color);
  }

  .footer a {
    color: var(--text-secondary);
    text-decoration: none;
    transition: color 0.2s;
  }
  .footer a:hover { color: var(--text-primary); }

  /* Mobile */
  @media (max-width: 640px) {
    .tasks-grid { grid-template-columns: 1fr; }
    .endpoints-grid { grid-template-columns: 1fr; }
    .endpoint-desc { display: none; }
    .actions-table { font-size: 12px; }
    .actions-table td:nth-child(3) { display: none; }
    .header { padding: 32px 0 16px; }
  }
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <header class="header">
    <div class="badge">
      <span class="pulse"></span>
      OpenEnv Environment &middot; Running
    </div>
    <h1>SRE Incident Response</h1>
    <p class="subtitle">
      An AI agent environment where agents act as on-call SRE engineers &mdash;
      triaging alerts, diagnosing root causes, applying fixes, and writing
      postmortems for realistic infrastructure incidents.
    </p>
    <div class="header-actions">
      <a href="/docs" class="btn btn-primary">&#x1f4d6; API Documentation</a>
      <a href="https://github.com/KartikAneja5/sre-incident-response" target="_blank" class="btn btn-secondary">&#x2B50; GitHub Repo</a>
      <a href="/tasks" class="btn btn-secondary">&#x1f4cb; List Tasks</a>
    </div>
  </header>

  <!-- Status -->
  <div class="status-bar">
    <div class="status-item">
      <span class="status-dot green"></span>
      Environment Active
    </div>
    <div class="status-item">
      <span class="status-dot blue"></span>
      v1.0.0
    </div>
    <div class="status-item">
      <span class="status-dot purple"></span>
      3 Tasks Available
    </div>
    <div class="status-item">
      <span class="status-dot blue"></span>
      OpenEnv Compatible
    </div>
  </div>

  <!-- Tasks -->
  <section class="section">
    <div class="section-title">&#x1f3af; Incident Scenarios</div>
    <div class="tasks-grid">
      <div class="task-card easy">
        <div class="task-header">
          <div class="task-name">Alert Triage</div>
          <span class="difficulty-badge easy">Easy</span>
        </div>
        <p class="task-desc">
          5 alerts firing simultaneously across a microservices stack. Identify db-primary
          CPU at 98% as the root cause driving cascading failures.
        </p>
        <div class="task-meta">
          <span>&#x23F1; 8 max steps</span>
          <span>&#x1f3c6; 8 grading criteria</span>
          <span>&#x1f4a1; alert_triage</span>
        </div>
      </div>
      <div class="task-card medium">
        <div class="task-header">
          <div class="task-name">Root Cause Diagnosis</div>
          <span class="difficulty-badge medium">Medium</span>
        </div>
        <p class="task-desc">
          Payment service is down (HTTP 503). A bad deploy introduced a slow SQL query
          that exhausted the DB connection pool. Can you find it?
        </p>
        <div class="task-meta">
          <span>&#x23F1; 10 max steps</span>
          <span>&#x1f3c6; 5 grading criteria</span>
          <span>&#x1f4a1; root_cause_diagnosis</span>
        </div>
      </div>
      <div class="task-card hard">
        <div class="task-header">
          <div class="task-name">Full Incident Runbook</div>
          <span class="difficulty-badge hard">Hard</span>
        </div>
        <p class="task-desc">
          Redis OOM &rarr; auth cache miss storm &rarr; mobile API circuit breaker &rarr;
          company-wide login outage. Fix the cascade and write the postmortem.
        </p>
        <div class="task-meta">
          <span>&#x23F1; 20 max steps</span>
          <span>&#x1f3c6; 9 grading criteria</span>
          <span>&#x1f4a1; full_incident_runbook</span>
        </div>
      </div>
    </div>
  </section>

  <!-- API Endpoints -->
  <section class="section">
    <div class="section-title">&#x26A1; API Endpoints</div>
    <div class="endpoints-grid">
      <div class="endpoint-card">
        <span class="method get">GET</span>
        <span class="endpoint-path">/health</span>
        <span class="endpoint-desc">Health check</span>
      </div>
      <div class="endpoint-card">
        <span class="method get">GET</span>
        <span class="endpoint-path">/tasks</span>
        <span class="endpoint-desc">List all tasks</span>
      </div>
      <div class="endpoint-card">
        <span class="method post">POST</span>
        <span class="endpoint-path">/reset</span>
        <span class="endpoint-desc">Start new episode</span>
      </div>
      <div class="endpoint-card">
        <span class="method post">POST</span>
        <span class="endpoint-path">/step</span>
        <span class="endpoint-desc">Execute an action</span>
      </div>
      <div class="endpoint-card">
        <span class="method get">GET</span>
        <span class="endpoint-path">/state</span>
        <span class="endpoint-desc">Current state</span>
      </div>
      <div class="endpoint-card">
        <span class="method get">GET</span>
        <span class="endpoint-path">/metrics</span>
        <span class="endpoint-desc">Server stats</span>
      </div>
      <div class="endpoint-card">
        <span class="method get">GET</span>
        <span class="endpoint-path">/docs</span>
        <span class="endpoint-desc">Swagger UI</span>
      </div>
    </div>
  </section>

  <!-- Action Types -->
  <section class="section">
    <div class="section-title">&#x1f3ae; Action Space</div>
    <table class="actions-table">
      <thead>
        <tr>
          <th>Action Type</th>
          <th>Purpose</th>
          <th>Example</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>acknowledge_alert</td>
          <td>Acknowledge &amp; classify a specific alert</td>
          <td>"CRITICAL: db-primary CPU > 95%"</td>
        </tr>
        <tr>
          <td>diagnose</td>
          <td>Provide root cause analysis</td>
          <td>"db-primary CPU overload causing cascade"</td>
        </tr>
        <tr>
          <td>run_query</td>
          <td>Query for specific log data</td>
          <td>"slow queries", "recent deploy"</td>
        </tr>
        <tr>
          <td>apply_fix</td>
          <td>Apply a remediation action</td>
          <td>"Rollback to v2.4.0"</td>
        </tr>
        <tr>
          <td>escalate</td>
          <td>Escalate to another team</td>
          <td>"Escalating to DBA team"</td>
        </tr>
        <tr>
          <td>write_postmortem</td>
          <td>Submit incident postmortem</td>
          <td>Full postmortem text with timeline</td>
        </tr>
        <tr>
          <td>noop</td>
          <td>Take no action this step</td>
          <td>""</td>
        </tr>
      </tbody>
    </table>
  </section>

  <!-- Reward -->
  <section class="section">
    <div class="section-title">&#x1f4ca; Reward System</div>
    <div class="grading-cards">
      <div class="grading-card">
        <h4>&#x2705; Cumulative &amp; Partial</h4>
        <p>Rewards are never binary. Each grading criterion has a specific weight.
           Total reward ranges from 0.0 to 1.0.</p>
        <div class="reward-bar"><div class="reward-fill" style="width: 77%"></div></div>
      </div>
      <div class="grading-card">
        <h4>&#x1f6a8; Penalties</h4>
        <p>&minus;0.05 for premature fixes, &minus;0.05 for unnecessary escalation,
           &minus;0.02 per noop after step 5. Floor is 0.0.</p>
        <div class="reward-bar"><div class="reward-fill" style="width: 100%"></div></div>
      </div>
      <div class="grading-card">
        <h4>&#x1f3c1; Episode End</h4>
        <p>Episode ends when total reward &ge; 0.95 (practical completion)
           or maximum steps are reached.</p>
        <div class="reward-bar"><div class="reward-fill" style="width: 95%"></div></div>
      </div>
    </div>
  </section>

  <!-- Baseline Scores -->
  <section class="section">
    <div class="section-title">&#x1f4ca; Baseline Scores — Qwen/Qwen2.5-72B-Instruct</div>
    <table class="actions-table">
      <thead>
        <tr>
          <th>Task</th>
          <th>Difficulty</th>
          <th>Steps Used</th>
          <th>Final Score</th>
          <th>Success</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>alert_triage</td>
          <td style="color: #4ade80;">Easy</td>
          <td>5 / 8</td>
          <td style="color: #4ade80; font-weight: 700;">1.00</td>
          <td>&#x2705;</td>
        </tr>
        <tr>
          <td>root_cause_diagnosis</td>
          <td style="color: #facc15;">Medium</td>
          <td>4 / 10</td>
          <td style="color: #4ade80; font-weight: 700;">1.00</td>
          <td>&#x2705;</td>
        </tr>
        <tr>
          <td>full_incident_runbook</td>
          <td style="color: #f87171;">Hard</td>
          <td>6 / 20</td>
          <td style="color: #4ade80; font-weight: 700;">1.00</td>
          <td>&#x2705;</td>
        </tr>
      </tbody>
    </table>
    <p style="text-align: center; margin-top: 16px; font-size: 13px; color: #64748b;">
      Zero-shot evaluation &middot; No few-shot prompting &middot;
      Average Score: <strong style="color: #4ade80;">1.00</strong>
    </p>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <p>
      Built for <strong>Meta &times; Hugging Face Hackathon</strong> using
      <a href="https://github.com/huggingface/openenv">OpenEnv</a>
      &middot; by <a href="https://github.com/KartikAneja5">Kartik Aneja</a>
    </p>
  </footer>

</div>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════
# System Endpoints
# ═══════════════════════════════════════════════════════════


@app.get("/", tags=["system"])
def root(request: Request):
    """Landing page — environment overview. Returns JSON for API clients, HTML for browsers."""
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return {
            "name": "sre-incident-response",
            "version": "1.0.0",
            "description": "OpenEnv SRE Incident Response environment",
            "status": "ok",
            "tasks": 3,
            "docs": "/docs",
            "health": "/health",
        }
    return HTMLResponse(LANDING_PAGE_HTML)


@app.get("/health", tags=["system"])
def health_check() -> Dict[str, Any]:
    """Health check endpoint. Always returns 200."""
    return {
        "status": "ok",
        "environment": "sre-incident-response",
        "version": "1.0.0",
        "tasks_available": 3,
        "active_sessions": len(sessions),
    }


@app.get("/metrics", response_model=MetricsModel, tags=["system"])
def get_metrics() -> MetricsModel:
    """Return server-level usage statistics."""
    avg_reward = (
        sum(_stats["rewards_history"]) / len(_stats["rewards_history"])
        if _stats["rewards_history"]
        else 0.0
    )
    return MetricsModel(
        total_resets=_stats["total_resets"],
        total_steps=_stats["total_steps"],
        total_episodes_completed=_stats["total_episodes_completed"],
        average_final_reward=round(avg_reward, 3),
        active_sessions=len(sessions),
    )


# ═══════════════════════════════════════════════════════════
# Environment Endpoints
# ═══════════════════════════════════════════════════════════


@app.post("/reset", response_model=ObservationModel, tags=["environment"])
def reset_environment(
    task_id: Optional[str] = Query(None, description="Task ID as query param"),
    request: Optional[ResetRequest] = Body(None),
    response: Response = None,
) -> ObservationModel:
    """
    Reset the environment for a new episode.

    Accepts task_id as a query parameter or in the request body.
    Returns the initial observation.
    Creates a new session — no state leakage between episodes.
    """
    # Create a fresh session
    session_id, env = create_session()

    # Resolve task_id: query param > body field > default to first task
    resolved_task_id = task_id
    if resolved_task_id is None and request is not None and request.task_id is not None:
        resolved_task_id = request.task_id
    if resolved_task_id is None:
        # Default to the first available task
        tasks = env.get_tasks()
        if tasks:
            resolved_task_id = tasks[0].id
        else:
            raise HTTPException(status_code=400, detail="No tasks available")
    try:
        observation = env.reset(resolved_task_id)

        # Embed session_id in observation
        observation.session_id = session_id
        if observation.hint is None:
            observation.hint = f"Session {session_id[:8]} started."
        else:
            observation.hint = f"Session {session_id[:8]} started. {observation.hint}"

        # Set response header
        if response is not None:
            response.headers["X-Session-ID"] = session_id

        # Increment stats
        _stats["total_resets"] += 1

        return observation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResultModel, tags=["environment"])
def step_environment(
    action: ActionModel,
    session_id: Optional[str] = Query(None, description="Session ID (optional, defaults to most recent)"),
) -> StepResultModel:
    """
    Execute one step in the environment.

    Accepts an action and returns the step result with observation,
    reward, done flag, success flag, and detailed info.
    Optionally pass session_id to target a specific session.
    """
    try:
        sid, env = get_or_create_session(session_id)
        result = env.step(action)

        # Increment stats
        _stats["total_steps"] += 1

        # Track completed episodes
        if result.done:
            _stats["total_episodes_completed"] += 1
            _stats["rewards_history"].append(result.reward)
            # Keep only last 100 rewards
            if len(_stats["rewards_history"]) > 100:
                _stats["rewards_history"] = _stats["rewards_history"][-100:]

        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=StateModel, tags=["environment"])
def get_state(
    session_id: Optional[str] = Query(None, description="Session ID (optional, defaults to most recent)"),
) -> StateModel:
    """
    Get the current environment state.

    Returns the current task, episode, step, reward, and grader scores.
    Optionally pass session_id to target a specific session.
    """
    try:
        sid, env = get_or_create_session(session_id)
        state = env.get_state()
        return state
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Module-level task list — computed once at startup, never changes
_TASK_LIST: Optional[List[TaskInfo]] = None


def _get_task_list() -> List[TaskInfo]:
    """Return cached task list, initializing once if needed."""
    global _TASK_LIST
    if _TASK_LIST is None:
        temp_env = SREEnvironment()
        _TASK_LIST = temp_env.get_tasks()
    return _TASK_LIST


@app.get("/tasks", response_model=List[TaskInfo], tags=["environment"])
def get_tasks() -> List[TaskInfo]:
    """
    Get a list of all available tasks.

    Returns task IDs, names, difficulties, max steps, and descriptions.
    Task list is cached at startup — no new environment instances created per request.
    """
    return _get_task_list()
