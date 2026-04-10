"""
FastAPI application for the SRE Incident Response OpenEnv environment.
All endpoints are implemented per the OpenEnv specification.
"""

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from environment import SREEnvironment
from models import (
    ActionModel,
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

# Global environment instance
env = SREEnvironment()


@app.get("/", tags=["system"])
def root() -> Dict[str, Any]:
    """Root endpoint — environment overview."""
    return {
        "name": "SRE Incident Response — OpenEnv Environment",
        "version": "1.0.0",
        "status": "running",
        "description": (
            "An OpenEnv environment where AI agents act as on-call SRE engineers. "
            "Agents must triage alerts, diagnose root causes, apply fixes, and write "
            "postmortems for realistic synthetic infrastructure incidents."
        ),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "tasks": "/tasks",
            "reset": "/reset  [POST]",
            "step": "/step  [POST]",
            "state": "/state",
        },
        "tasks": [t.model_dump() for t in env.get_tasks()],
    }


@app.get("/health", tags=["system"])
def health_check() -> Dict[str, str]:
    """Health check endpoint. Always returns 200."""
    return {"status": "ok"}


@app.post("/reset", response_model=ObservationModel, tags=["environment"])
def reset_environment(request: ResetRequest) -> ObservationModel:
    """
    Reset the environment for a new episode.

    Accepts a task_id and returns the initial observation.
    All previous state is cleared — no state leakage between episodes.
    """
    try:
        observation = env.reset(request.task_id)
        return observation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResultModel, tags=["environment"])
def step_environment(action: ActionModel) -> StepResultModel:
    """
    Execute one step in the environment.

    Accepts an action and returns the step result with observation,
    reward, done flag, success flag, and detailed info.
    """
    try:
        result = env.step(action)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=StateModel, tags=["environment"])
def get_state() -> StateModel:
    """
    Get the current environment state.

    Returns the current task, episode, step, reward, and grader scores.
    """
    try:
        state = env.get_state()
        return state
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks", response_model=List[TaskInfo], tags=["environment"])
def get_tasks() -> List[TaskInfo]:
    """
    Get a list of all available tasks.

    Returns task IDs, names, difficulties, max steps, and descriptions.
    """
    return env.get_tasks()
