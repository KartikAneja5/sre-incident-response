"""Tasks package for SRE Incident Response environment."""

from tasks.alert_triage import AlertTriageTask
from tasks.root_cause import RootCauseDiagnosisTask
from tasks.full_runbook import FullIncidentRunbookTask

TASK_REGISTRY = {
    "alert_triage": AlertTriageTask,
    "root_cause_diagnosis": RootCauseDiagnosisTask,
    "full_incident_runbook": FullIncidentRunbookTask,
}

__all__ = [
    "AlertTriageTask",
    "RootCauseDiagnosisTask",
    "FullIncidentRunbookTask",
    "TASK_REGISTRY",
]
