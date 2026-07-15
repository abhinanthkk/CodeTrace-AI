"""Tests for the TraceSerializer."""

import pytest
from app.tracing.serializer import TraceSerializer


class TestTraceSerializer:
    def setup_method(self):
        self.s = TraceSerializer()

    def test_none(self):
        assert self.s.serialize(None) is None

    def test_bool(self):
        assert self.s.serialize(True) is True
        assert self.s.serialize(False) is False

    def test_int(self):
        assert self.s.serialize(42) == 42
        assert self.s.serialize(-7) == -7

    def test_large_int(self):
        huge = 2**60
        result = self.s.serialize(huge)
        assert isinstance(result, str)
        assert "1152921504606846976" in result

    def test_float(self):
        assert self.s.serialize(3.14) == 3.14

    def test_string(self):
        assert self.s.serialize("hello") == "hello"

    def test_long_string_truncation(self):
        s = TraceSerializer(max_string=10)
        result = s.serialize("a" * 100)
        assert len(result) <= 10 + len("...<truncated>")
        assert "...<truncated>" in result

    def test_list(self):
        assert self.s.serialize([1, 2, 3]) == [1, 2, 3]

    def test_list_truncation(self):
        s = TraceSerializer(max_items=3)
        result = s.serialize(list(range(10)))
        assert len(result) <= 4  # 3 items + truncation marker
        assert any("...<" in str(v) for v in result)

    def test_tuple(self):
        assert self.s.serialize((1, 2)) == [1, 2]

    def test_set(self):
        result = self.s.serialize({3, 1, 2})
        assert sorted(result) == [1, 2, 3]

    def test_dict(self):
        result = self.s.serialize({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_dict_truncation(self):
        s = TraceSerializer(max_items=2)
        result = s.serialize({f"k{i}": i for i in range(10)})
        assert len(result) <= 3  # 2 items + truncation marker

    def test_nested_depth_limit(self):
        s = TraceSerializer(max_depth=2)
        obj = {"a": {"b": {"c": {"d": 1}}}}
        result = s.serialize(obj)
        # Should not recurse infinitely
        assert isinstance(result, dict)

    def test_bytes(self):
        result = self.s.serialize(b"hello")
        assert "bytes" in result

    def test_custom_object(self):
        class Foo:
            pass
        result = self.s.serialize(Foo())
        assert "Foo" in result

    def test_depth_limit_stops_recursion(self):
        s = TraceSerializer(max_depth=2)
        # Self-referencing dict would infinite-loop without depth limit
        d: dict = {"a": 1}
        d["self"] = d
        result = s.serialize(d)
        assert isinstance(result, dict)

    def test_locals_filtering(self):
        """Serializer should exclude internal variables from frame locals."""
        from app.tracing.tracer import PythonTracer
        tracer = PythonTracer.__new__(PythonTracer)
        frame_locals = {
            "__name__": "__main__",
            "__file__": "test.py",
            "x": 5,
            "y": 10,
            "_trace_fn": lambda: None,
        }
        result = self.s.serialize_locals(frame_locals)
        assert "x" in result
        assert "y" in result
        assert "__name__" not in result
        assert "__file__" not in result
        assert "_trace_fn" not in result
