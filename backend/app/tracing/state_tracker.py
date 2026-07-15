"""
CodeTrace AI — Variable State Tracker

Compares consecutive variable snapshots and produces structured change
records: created, updated, and deleted.

Detects:
- Variable created (exists in current, not in previous)
- Variable updated (different value between current and previous)
- Variable deleted (exists in previous, not in current)

Handles mutable objects correctly by operating on safe snapshots — never
on live frame.f_locals references.
"""

from typing import Any


class StateTracker:
    """
    Tracks variable state across execution steps.

    Usage:
        tracker = StateTracker()
        prev = {"x": 5, "i": 1}
        curr = {"x": 5, "i": 2}
        changes = tracker.compare(prev, curr)
        # => {"i": {"type": "updated", "old_value": 1, "new_value": 2}}
    """

    def compare(
        self,
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """
        Compare two variable state snapshots.

        Returns a dict mapping variable name to a change descriptor:
          {"type": "created", "value": ...}
          {"type": "updated", "old_value": ..., "new_value": ...}
          {"type": "deleted", "old_value": ...}
        """
        changes: dict[str, dict[str, Any]] = {}
        all_names = set(previous.keys()) | set(current.keys())

        for name in sorted(all_names):
            in_prev = name in previous
            in_curr = name in current

            if not in_prev and in_curr:
                changes[name] = {
                    "type": "created",
                    "value": current[name],
                }
            elif in_prev and not in_curr:
                changes[name] = {
                    "type": "deleted",
                    "old_value": previous[name],
                }
            elif in_prev and in_curr:
                prev_val = previous[name]
                curr_val = current[name]
                if not self._values_equal(prev_val, curr_val):
                    changes[name] = {
                        "type": "updated",
                        "old_value": prev_val,
                        "new_value": curr_val,
                    }

        return changes

    def _values_equal(self, a: Any, b: Any) -> bool:
        """
        Compare two serialized values for equality.

        After serialization, most values are JSON-safe primitives and can
        be compared directly. For nested structures (lists, dicts), the
        default __eq__ works correctly since we operate on safe copies.
        """
        if type(a) != type(b):
            return False
        try:
            return a == b
        except Exception:
            return False
