"""Tests for railyard.log."""

import json
import tempfile
from pathlib import Path

from railyard.log import TransitionLog


class TestTransitionLog:
    def test_append_and_history(self):
        log = TransitionLog()
        log.append(from_state="a", to_state="b", action="go")
        log.append(from_state="b", to_state="c", action="finish", context_snapshot={"x": 1})
        assert len(log) == 2
        history = log.get_history()
        assert history[0]["from"] == "a"
        assert history[1]["context_snapshot"] == {"x": 1}

    def test_iter(self):
        log = TransitionLog()
        log.append(from_state="a", to_state="b", action="go")
        entries = list(log)
        assert len(entries) == 1

    def test_save_and_load(self, tmp_path):
        log = TransitionLog()
        log.append(from_state="a", to_state="b", action="go")
        log.append(from_state="b", to_state="c", action="finish")

        path = tmp_path / "transitions.jsonl"
        log.save(path)

        assert path.exists()
        loaded = TransitionLog.load(path)
        assert len(loaded) == 2
        assert loaded.get_history()[0]["from"] == "a"
        assert loaded.get_history()[1]["to"] == "c"

    def test_load_nonexistent(self, tmp_path):
        log = TransitionLog.load(tmp_path / "nope.jsonl")
        assert len(log) == 0

    def test_jsonl_format(self, tmp_path):
        log = TransitionLog()
        log.append(from_state="x", to_state="y", action="move")
        path = tmp_path / "test.jsonl"
        log.save(path)

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["from"] == "x"
        assert "timestamp" in data
