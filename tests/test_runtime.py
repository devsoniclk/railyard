"""Tests for railyard.runtime."""

import pytest

from railyard.machine import Machine, state
from railyard.runtime import Runtime, AgentAction, InvalidTransition, Session


def _build_machine() -> Machine:
    m = Machine(start="draft")
    m.add(state("draft", tools=["write", "edit"]))
    m.add(state("review", tools=["comment", "approve"]))
    m.add(state("done", terminal=True))
    m.allow("draft -> review")
    m.allow("review -> done", guard=lambda ctx: ctx.get("approved", False))
    m.allow("review -> draft")
    m.validate()
    return m


class TestRuntime:
    def test_initial_state(self):
        rt = Runtime(_build_machine())
        assert rt.current_state == "draft"

    def test_allowed_tools(self):
        rt = Runtime(_build_machine())
        assert rt.allowed_tools == ["write", "edit"]

    def test_is_terminal(self):
        rt = Runtime(_build_machine())
        assert rt.is_terminal is False

    def test_validate_good_transition(self):
        rt = Runtime(_build_machine())
        action = AgentAction("edit", "review")
        rt.validate_transition(action, {})  # should not raise

    def test_validate_bad_tool(self):
        rt = Runtime(_build_machine())
        action = AgentAction("deploy", "review")
        with pytest.raises(InvalidTransition, match="not allowed"):
            rt.validate_transition(action, {})

    def test_validate_bad_target(self):
        rt = Runtime(_build_machine())
        action = AgentAction("edit", "done")
        with pytest.raises(InvalidTransition, match="No transition"):
            rt.validate_transition(action, {})

    def test_validate_guard_rejects(self):
        rt = Runtime(_build_machine())
        # move to review first
        rt.execute(AgentAction("edit", "review"), {})
        action = AgentAction("approve", "done")
        with pytest.raises(InvalidTransition, match="Guard rejected"):
            rt.validate_transition(action, {"approved": False})

    def test_execute_advances_state(self):
        rt = Runtime(_build_machine())
        rt.execute(AgentAction("edit", "review"), {})
        assert rt.current_state == "review"

    def test_execute_logs(self):
        rt = Runtime(_build_machine())
        rt.execute(AgentAction("edit", "review"), {"x": 1})
        assert len(rt.log) == 1
        entry = rt.log.get_history()[0]
        assert entry["from"] == "draft"
        assert entry["to"] == "review"
        assert entry["action"] == "edit"


class TestSession:
    def test_step(self):
        m = _build_machine()

        def agent(rt, ctx):
            return AgentAction("edit", "review")

        with m.run(agent) as session:
            action = session.step()
            assert action.tool == "edit"
            assert session.current_state == "review"

    def test_step_rejects_illegal(self):
        m = _build_machine()

        def bad_agent(rt, ctx):
            return AgentAction("edit", "done")  # illegal jump

        with m.run(bad_agent) as session:
            with pytest.raises(InvalidTransition):
                session.step()

    def test_run_until_done(self):
        m = _build_machine()
        steps = iter(
            [
                AgentAction("edit", "review"),
                AgentAction("approve", "done"),
            ]
        )

        def agent(rt, ctx):
            return next(steps)

        with m.run(agent) as session:
            actions = session.run_until_done({"approved": True})
            assert len(actions) == 2
            assert session.is_terminal

    def test_terminal_blocks_further_steps(self):
        m = _build_machine()
        steps = iter(
            [
                AgentAction("edit", "review"),
                AgentAction("approve", "done"),
            ]
        )

        def agent(rt, ctx):
            return next(steps)

        with m.run(agent) as session:
            session.run_until_done({"approved": True})
            with pytest.raises(InvalidTransition, match="already finished"):
                session.step()

    def test_context_manager(self):
        m = _build_machine()

        def agent(rt, ctx):
            return AgentAction("edit", "review")

        with m.run(agent) as session:
            assert isinstance(session, Session)
