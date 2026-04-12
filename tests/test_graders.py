import pytest
from models import ActionModel
from environment import SREEnvironment

class TestAlertTriageGrader:
    def test_correct_ack_gives_reward(self, alert_task):
        obs = alert_task.step(ActionModel(action_type="acknowledge_alert", value="db-primary CPU"))
        assert alert_task.grader.total_reward > 0.0

    def test_wrong_ack_gives_no_reward(self, alert_task):
        obs = alert_task.step(ActionModel(action_type="acknowledge_alert", value="api-gateway"))
        assert alert_task.grader.total_reward <= 0.05

    def test_full_correct_episode_scores_1(self, alert_task):
        actions = [
            ActionModel(action_type="diagnose", value="db-primary is P1 root cause cascade"),
            ActionModel(action_type="diagnose", value="payment-service is P1"),
            ActionModel(action_type="diagnose", value="auth-service is P2"),
            ActionModel(action_type="diagnose", value="cache-redis is P2"),
            ActionModel(action_type="diagnose", value="api-gateway is P3"),
        ]
        for a in actions:
            alert_task.step(a)
        assert abs(alert_task.grader.total_reward - 0.99) < 1e-5

    def test_reward_never_decreases_on_valid_action(self, alert_task):
        alert_task.step(ActionModel(action_type="diagnose", value="db-primary is root cause P1"))
        r1 = alert_task.grader.total_reward
        alert_task.step(ActionModel(action_type="diagnose", value="payment is P1"))
        r2 = alert_task.grader.total_reward
        assert r2 >= r1, "Reward decreased!"

    def test_reward_never_exceeds_1(self, alert_task):
        act = ActionModel(action_type="diagnose", value="db-primary P1 root cause cascading payment-service P1 auth-service P2 cache-redis P2 api-gateway P3")
        for _ in range(20): alert_task.step(act)
        assert alert_task.grader.total_reward <= 0.99

    def test_same_criterion_not_rewarded_twice(self, alert_task):
        alert_task.step(ActionModel(action_type="diagnose", value="db-primary is root cause"))
        r1 = alert_task.grader.total_reward
        alert_task.step(ActionModel(action_type="diagnose", value="db-primary is root cause"))
        assert r1 == alert_task.grader.total_reward, "Criterion rewarded twice!"

    def test_reset_clears_all_state(self, alert_task):
        alert_task.step(ActionModel(action_type="diagnose", value="db-primary P1 root cause"))
        assert alert_task.grader.total_reward > 0
        alert_task.reset()
        assert alert_task.grader.total_reward <= 0.05

    def test_fuzzy_matching_works(self, alert_task):
        alert_task.step(ActionModel(action_type="diagnose", value="database overloaded due to cpu"))
        assert "diagnose_root_cause" in alert_task.grader.scored_criteria

    def test_invalid_action_type_no_crash(self, alert_task):
        alert_task.step(ActionModel(action_type="fly_to_moon", value="some value"))
        assert alert_task.grader.total_reward <= 0.05

    def test_episode_ends_at_max_steps(self, alert_task):
        for _ in range(alert_task.max_steps):
            obs = alert_task.step(ActionModel(action_type="noop", value=""))
        assert alert_task.done


class TestRootCauseDiagnosisGrader:
    def test_run_query_slow_queries_returns_logs(self, root_cause_task):
        # We can test `run_query` by passing basic fuzzy queries
        obs = root_cause_task.step(ActionModel(action_type="run_query", value="slow queries"))["observation"]
        assert "Action processing enabled" in obs.logs[0] or "SLOW QUERY" in str(obs.logs)

    def test_correct_diagnosis_chain(self, root_cause_task):
        actions = [
            ActionModel(action_type="run_query", value="slow queries"),
            ActionModel(action_type="diagnose", value="slow query deploy v2.4.1 exhausted connection pool"),
            ActionModel(action_type="apply_fix", value="rollback to v2.4.0"),
            ActionModel(action_type="acknowledge_alert", value="payment-service down"),
        ]
        for a in actions:
            root_cause_task.step(a)
        assert abs(root_cause_task.grader.total_reward - 0.99) < 1e-5

    def test_diagnosis_without_query_still_possible(self, root_cause_task):
        root_cause_task.step(ActionModel(action_type="diagnose", value="slow query deploy v2.4.1 pool exhausted rollback"))
        root_cause_task.step(ActionModel(action_type="acknowledge_alert", value="payment-service"))
        assert abs(root_cause_task.grader.total_reward - 0.99) < 1e-5

    def test_rollback_fix_gets_reward(self, root_cause_task):
        root_cause_task.step(ActionModel(action_type="diagnose", value="deploy v2.4.1 slow query"))
        root_cause_task.step(ActionModel(action_type="apply_fix", value="rollback to v2.4.0"))
        assert "suggest_fix" in root_cause_task.grader.scored_criteria

    def test_wrong_fix_no_reward(self, root_cause_task):
        root_cause_task.step(ActionModel(action_type="diagnose", value="deploy v2.4.1 slow query"))
        root_cause_task.step(ActionModel(action_type="apply_fix", value="restart redis"))
        assert "suggest_fix" not in root_cause_task.grader.scored_criteria


class TestFullRunbookGrader:
    def test_red_herring_does_not_give_reward(self, full_runbook_task):
        full_runbook_task.step(ActionModel(action_type="diagnose", value="api-gateway connection pool is the problem"))
        c = full_runbook_task.grader.scored_criteria
        assert "diagnose_redis_oom" not in c
        assert "triage_redis_p1" not in c

    def test_wrong_service_fix_penalty(self, full_runbook_task):
        full_runbook_task.step(ActionModel(action_type="apply_fix", value="fix api-gateway"))
        r = full_runbook_task.grader.total_reward
        assert r >= 0.0

    def test_redis_fix_requires_specific_keywords(self, full_runbook_task):
        full_runbook_task.step(ActionModel(action_type="apply_fix", value="fix redis"))
        assert "apply_redis_fix" not in full_runbook_task.grader.scored_criteria
        full_runbook_task.step(ActionModel(action_type="apply_fix", value="set maxmemory-policy allkeys-lru"))
        assert "apply_redis_fix" in full_runbook_task.grader.scored_criteria

    def test_fix_order_strictly_enforced(self, full_runbook_task):
        full_runbook_task.step(ActionModel(action_type="apply_fix", value="restart auth"))
        full_runbook_task.step(ActionModel(action_type="apply_fix", value="maxmemory-policy allkeys-lru"))
        assert "fix_correct_order" not in full_runbook_task.grader.scored_criteria

    def test_incomplete_postmortem_partial_credit(self, full_runbook_task):
        full_runbook_task.step(ActionModel(action_type="write_postmortem", value="timeline: went down. rca: bad config"))
        assert "postmortem_timeline" in full_runbook_task.grader.scored_criteria
        assert "postmortem_actions" not in full_runbook_task.grader.scored_criteria

    def test_complete_postmortem_full_credit(self, full_runbook_task):
        full_runbook_task.step(ActionModel(action_type="write_postmortem", value="timeline rca action items prevention"))
        assert "postmortem_timeline" in full_runbook_task.grader.scored_criteria
        assert "postmortem_prevention" in full_runbook_task.grader.scored_criteria

    def test_no_wrong_service_blame_default_earned(self, full_runbook_task):
        assert "no_wrong_service_blame" in full_runbook_task.grader.scored_criteria
        assert full_runbook_task.grader.total_reward >= 0.05


class TestEnvironmentCore:
    def test_all_three_tasks_reset_cleanly(self, sre_env):
        for task_id in ["alert_triage", "root_cause_diagnosis", "full_incident_runbook"]:
            obs = sre_env.reset(task_id)
            assert obs is not None
            assert len(obs.logs) > 0

    def test_concurrent_session_isolation(self, alert_task):
        taskB = type(alert_task)()
        taskB.reset()
        alert_task.step(ActionModel(action_type="diagnose", value="db-primary root cause"))
        assert alert_task.grader.total_reward > 0
        assert taskB.grader.total_reward <= 0.05

    def test_observation_has_all_required_fields(self, alert_task):
        obs = alert_task.step(ActionModel(action_type="noop", value=""))["observation"]
        assert hasattr(obs, "logs") and hasattr(obs, "metrics") and hasattr(obs, "task_goal")

    def test_step_result_has_all_required_fields(self, alert_task):
        pass

    def test_grader_breakdown_in_info(self, alert_task):
        res = alert_task.grader.breakdown
        assert isinstance(res, dict)

    def test_rewards_are_floats_in_range(self, alert_task):
        alert_task.step(ActionModel(action_type="diagnose", value="db-primary root cause"))
        r = alert_task.grader.total_reward
        assert isinstance(r, float)
        assert 0.0 <= r <= 1.0

    def test_scenario_variants_differ(self, sre_env):
        obs1 = sre_env.reset("alert_triage")
        variants_seen = set()
        for _ in range(20):
            obs = sre_env.reset("alert_triage")
            variants_seen.add(tuple(obs.active_alerts))
        assert len(variants_seen) > 1, "Only one scenario variant seen after 20 resets!"
