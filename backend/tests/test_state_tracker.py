"""Tests for the StateTracker."""

import pytest
from app.tracing.state_tracker import StateTracker


class TestStateTracker:
    def setup_method(self):
        self.tracker = StateTracker()

    def test_variable_created(self):
        changes = self.tracker.compare({}, {"x": 5})
        assert "x" in changes
        assert changes["x"]["type"] == "created"
        assert changes["x"]["value"] == 5

    def test_variable_updated(self):
        changes = self.tracker.compare({"x": 5}, {"x": 10})
        assert "x" in changes
        assert changes["x"]["type"] == "updated"
        assert changes["x"]["old_value"] == 5
        assert changes["x"]["new_value"] == 10

    def test_variable_deleted(self):
        changes = self.tracker.compare({"x": 5}, {})
        assert "x" in changes
        assert changes["x"]["type"] == "deleted"
        assert changes["x"]["old_value"] == 5

    def test_no_change(self):
        changes = self.tracker.compare({"x": 5, "y": 10}, {"x": 5, "y": 10})
        assert len(changes) == 0

    def test_multiple_changes(self):
        prev = {"a": 1, "b": 2, "c": 3}
        curr = {"a": 1, "b": 20, "d": 4}
        changes = self.tracker.compare(prev, curr)
        assert "b" in changes  # updated
        assert "c" in changes  # deleted
        assert "d" in changes  # created
        assert "a" not in changes

    def test_list_value_change(self):
        changes = self.tracker.compare({"arr": [1, 2]}, {"arr": [1, 2, 3]})
        assert "arr" in changes
        assert changes["arr"]["type"] == "updated"

    def test_none_to_value(self):
        changes = self.tracker.compare({"x": None}, {"x": 5})
        assert "x" in changes
        assert changes["x"]["type"] == "updated"

    def test_string_change(self):
        changes = self.tracker.compare({"name": "Alice"}, {"name": "Bob"})
        assert "name" in changes
        assert changes["name"]["type"] == "updated"
