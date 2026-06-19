"""Tests for railyard.machine."""

import pytest

from railyard.machine import Machine, MachineError, State, Transition, state


class TestState:
    def test_creation(self):
        s = state("draft", tools=["write", "edit"])
        assert s.name == "draft"
        assert s.tools == ["write", "edit"]
        assert s.terminal is False

    def test_terminal(self):
        s = state("done", terminal=True)
        assert s.terminal is True

    def test_equality(self):
        assert state("a") == state("a")
        assert state("a") != state("b")

    def test_hash(self):
        assert hash(state("a")) == hash(state("a"))


class TestTransition:
    def test_open_transition(self):
        t = Transition(from_state="a", to_state="b")
        assert t.is_allowed({}) is True

    def test_guard_passes(self):
        t = Transition(from_state="a", to_state="b", guard=lambda ctx: ctx.get("ok"))
        assert t.is_allowed({"ok": True}) is True

    def test_guard_fails(self):
        t = Transition(from_state="a", to_state="b", guard=lambda ctx: ctx.get("ok"))
        assert t.is_allowed({"ok": False}) is False
        assert t.is_allowed({}) is False

    def test_guard_exception(self):
        def bad_guard(ctx):
            raise ValueError("boom")

        t = Transition(from_state="a", to_state="b", guard=bad_guard)
        assert t.is_allowed({}) is False

    def test_repr(self):
        t = Transition(from_state="a", to_state="b")
        assert "open" in repr(t)
        t2 = Transition(from_state="a", to_state="b", guard=lambda c: True)
        assert "guarded" in repr(t2)


class TestMachine:
    def _simple_machine(self) -> Machine:
        m = Machine(start="a")
        m.add(state("a", tools=["tool_a"]))
        m.add(state("b", tools=["tool_b"]))
        m.add(state("c", tools=["tool_c"], terminal=True))
        m.allow("a -> b")
        m.allow("b -> c")
        return m

    def test_add_states(self):
        m = self._simple_machine()
        assert m.state_names == ["a", "b", "c"]

    def test_duplicate_state(self):
        m = Machine(start="a")
        m.add(state("a"))
        with pytest.raises(MachineError, match="Duplicate"):
            m.add(state("a"))

    def test_allow_bad_spec(self):
        m = Machine(start="a")
        m.add(state("a"))
        with pytest.raises(MachineError, match="Bad transition spec"):
            m.allow("a=>b")

    def test_allow_unknown_state(self):
        m = Machine(start="a")
        m.add(state("a"))
        with pytest.raises(MachineError, match="Unknown state"):
            m.allow("a -> b")

    def test_start_state(self):
        m = self._simple_machine()
        assert m.start_state == "a"

    def test_get_allowed_tools(self):
        m = self._simple_machine()
        assert m.get_allowed_tools("a") == ["tool_a"]
        assert m.get_allowed_tools("c") == ["tool_c"]

    def test_get_transitions(self):
        m = self._simple_machine()
        ts = m.get_transitions("a")
        assert len(ts) == 1
        assert ts[0].to_state == "b"

    def test_get_transition(self):
        m = self._simple_machine()
        t = m.get_transition("a", "b")
        assert t is not None
        assert m.get_transition("a", "c") is None

    def test_validate_ok(self):
        m = self._simple_machine()
        m.validate()  # should not raise

    def test_validate_bad_start(self):
        m = Machine(start="missing")
        with pytest.raises(MachineError, match="Start state"):
            m.validate()

    def test_validate_unreachable(self):
        m = Machine(start="a")
        m.add(state("a"))
        m.add(state("orphan"))
        m.allow("a -> a")  # self-loop, orphan is unreachable
        with pytest.raises(MachineError, match="Unreachable"):
            m.validate()

    def test_validate_dead_end(self):
        m = Machine(start="a")
        m.add(state("a"))
        m.add(state("b"))  # non-terminal with no outgoing transitions
        m.allow("a -> b")
        with pytest.raises(MachineError, match="dead end|outgoing"):
            m.validate()

    def test_chaining(self):
        m = Machine(start="a")
        result = m.add(state("a")).add(state("b", terminal=True)).allow("a -> b")
        assert result is m
