"""Tests for railyard.replay."""

from railyard.machine import Machine, state
from railyard.log import TransitionLog
from railyard.replay import Replay, ReplayResult


def _build_machine() -> Machine:
    m = Machine(start="draft")
    m.add(state("draft", tools=["write"]))
    m.add(state("review", tools=["comment", "approve"]))
    m.add(state("done", terminal=True))
    m.allow("draft -> review")
    m.allow("review -> done", guard=lambda ctx: ctx.get("approved", False))
    m.allow("review -> draft")
    m.validate()
    return m


class TestReplay:
    def test_valid_replay(self):
        m = _build_machine()
        log = TransitionLog()
        log.append(from_state="draft", to_state="review", action="submit")
        log.append(
            from_state="review",
            to_state="done",
            action="approve",
            context_snapshot={"approved": True},
        )

        result = Replay(m).check(log)
        assert result.valid is True
        assert result.total_steps == 2
        assert len(result.errors) == 0

    def test_bool(self):
        assert ReplayResult(valid=True, total_steps=1)
        assert not ReplayResult(valid=False, total_steps=1, errors=[{"x": 1}])

    def test_invalid_transition(self):
        m = _build_machine()
        log = TransitionLog()
        log.append(from_state="draft", to_state="done", action="skip")

        result = Replay(m).check(log)
        assert result.valid is False
        assert result.errors[0]["type"] == "invalid_transition"

    def test_state_mismatch(self):
        m = _build_machine()
        log = TransitionLog()
        log.append(from_state="review", to_state="done", action="approve")

        result = Replay(m).check(log)
        assert result.valid is False
        assert result.errors[0]["type"] == "state_mismatch"

    def test_guard_failure(self):
        m = _build_machine()
        log = TransitionLog()
        log.append(from_state="draft", to_state="review", action="submit")
        log.append(
            from_state="review",
            to_state="done",
            action="approve",
            context_snapshot={"approved": False},
        )

        result = Replay(m).check(log)
        assert result.valid is False
        assert any(e["type"] == "guard_failed" for e in result.errors)

    def test_empty_log(self):
        m = _build_machine()
        log = TransitionLog()
        result = Replay(m).check(log)
        assert result.valid is True
        assert result.total_steps == 0
