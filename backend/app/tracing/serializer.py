"""
CodeTrace AI — Safe Value Serializer

Produces JSON-safe representations of arbitrary Python objects.
Never crashes — unsupported types get a safe string representation.

Limits:
- Max string length: 500 chars
- Max collection items: 50
- Max nesting depth: 4
- Max repr length for unknown types: 200 chars

These limits prevent trace responses from becoming enormous when a
user's code contains large data structures.
"""

from typing import Any

# Tunable limits
MAX_STRING_LENGTH = 500
MAX_COLLECTION_ITEMS = 50
MAX_DEPTH = 4
MAX_REPR_LENGTH = 200


class TraceSerializer:
    """
    Serialize Python values into JSON-safe representations.

    Usage:
        serializer = TraceSerializer()
        safe = serializer.serialize(some_value)
        json.dumps(safe)  # guaranteed not to crash
    """

    def __init__(
        self,
        max_string: int = MAX_STRING_LENGTH,
        max_items: int = MAX_COLLECTION_ITEMS,
        max_depth: int = MAX_DEPTH,
        max_repr: int = MAX_REPR_LENGTH,
    ):
        self.max_string = max_string
        self.max_items = max_items
        self.max_depth = max_depth
        self.max_repr = max_repr

    def serialize(self, obj: Any) -> Any:
        """Serialize any value to a JSON-safe representation."""
        return self._serialize(obj, depth=0)

    def _serialize(self, obj: Any, depth: int) -> Any:
        if depth >= self.max_depth:
            return self._safe_repr(obj)

        if obj is None:
            return None
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, int):
            return self._serialize_int(obj)
        if isinstance(obj, float):
            return obj
        if isinstance(obj, str):
            return self._serialize_string(obj)
        if isinstance(obj, bytes):
            return f"<bytes: {len(obj)} bytes>"
        if isinstance(obj, (list, tuple)):
            return self._serialize_sequence(obj, depth)
        if isinstance(obj, set):
            return self._serialize_set(obj, depth)
        if isinstance(obj, dict):
            return self._serialize_dict(obj, depth)
        # Unsupported type — safe representation
        return self._safe_repr(obj)

    def _serialize_int(self, obj: int) -> int | str:
        """Handle integers too large for JSON (exceeds 2^53)."""
        if obj > 2**53 or obj < -(2**53):
            return repr(obj)
        return obj

    def _serialize_string(self, obj: str) -> str:
        if len(obj) > self.max_string:
            return obj[:self.max_string] + "...<truncated>"
        return obj

    def _serialize_sequence(self, obj: list | tuple, depth: int) -> list:
        items = list(obj)
        if len(items) > self.max_items:
            result = [self._serialize(v, depth + 1) for v in items[:self.max_items]]
            result.append(f"...<{len(items) - self.max_items} more items>")
            return result
        return [self._serialize(v, depth + 1) for v in items]

    def _serialize_set(self, obj: set, depth: int) -> list:
        """Sets aren't JSON-serializable — convert to sorted list when possible."""
        items = list(obj)
        if len(items) > self.max_items:
            result = self._sortable_list(items[:self.max_items], depth)
            result.append(f"...<{len(items) - self.max_items} more items>")
            return result
        return self._sortable_list(items, depth)

    def _sortable_list(self, items: list, depth: int) -> list:
        """Serialize items, attempting to sort if all same type."""
        serialized = [self._serialize(v, depth + 1) for v in items]
        try:
            serialized.sort(key=lambda x: str(x))
        except (TypeError, AttributeError):
            pass
        return serialized

    def _serialize_dict(self, obj: dict, depth: int) -> dict:
        result = {}
        count = 0
        for k, v in obj.items():
            if count >= self.max_items:
                result["...<truncated>"] = f"{len(obj) - count} more keys"
                break
            safe_key = self._serialize(k, depth + 1)
            # Dict keys in JSON must be strings
            key_str = str(safe_key) if not isinstance(safe_key, str) else safe_key
            result[key_str] = self._serialize(v, depth + 1)
            count += 1
        return result

    def _safe_repr(self, obj: Any) -> str:
        """Never-crashing representation of any object."""
        try:
            r = repr(obj)
            if len(r) > self.max_repr:
                return r[:self.max_repr] + "..."
            return f"<{type(obj).__name__}: {r}>"
        except Exception:
            return f"<{type(obj).__name__} at {id(obj):#x}>"

    def serialize_locals(self, frame_locals: dict[str, Any]) -> dict[str, Any]:
        """
        Serialize frame.f_locals, filtering out internal/tracer variables.

        Excludes:
        - Dunder names (__*__)
        - Tracer-internal variables
        - References to the tracer itself
        """
        snapshot: dict[str, Any] = {}
        for name, value in frame_locals.items():
            if self._is_internal(name, value):
                continue
            snapshot[name] = self._serialize(value, depth=0)
        return snapshot

    def _is_internal(self, name: str, value: Any) -> bool:
        """Check if a variable should be excluded from the trace."""
        if name.startswith("__") and name.endswith("__"):
            return True
        # Filter known tracer-internal names
        if name in (
            "_trace_fn", "_prev_locals", "_prev_line",
            "_serializer", "_state_tracker",
        ):
            return True
        # Skip references to tracer classes
        type_name = type(value).__name__
        if type_name in ("PythonTracer", "TraceSerializer", "StateTracker", "TraceProcessor"):
            return True
        return False
