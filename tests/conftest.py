import pytest
import random
from environment import SREEnvironment
from tasks.alert_triage import AlertTriageTask
from tasks.root_cause import RootCauseDiagnosisTask
from tasks.full_runbook import FullIncidentRunbookTask
from data.scenarios import TASK_SCENARIOS

@pytest.fixture(autouse=True)
def make_tests_deterministic(request):
    """
    Ensure grader unit tests rely exclusively on Variant 0 (the standard scenario). 
    Random variance remains unpatched ONLY for the dedicated `test_scenario_variants_differ` check.
    """
    if "test_scenario_variants_differ" not in request.node.name:
        original_choice = random.choice
        def dummy_choice(seq):
            return seq[0]
        random.choice = dummy_choice
        yield
        random.choice = original_choice
    else:
        yield

@pytest.fixture
def alert_task():
    task = AlertTriageTask()
    task.reset()
    return task

@pytest.fixture
def root_cause_task():
    task = RootCauseDiagnosisTask()
    task.reset()
    return task

@pytest.fixture
def full_runbook_task():
    task = FullIncidentRunbookTask()
    task.reset()
    return task

@pytest.fixture
def sre_env():
    return SREEnvironment()
