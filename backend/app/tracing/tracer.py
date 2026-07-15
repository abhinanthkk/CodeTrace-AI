"""
CodeTrace AI — Python Runtime Tracer

Uses sys.settrace() to capture every execution event in a user's Python
program: line execution, function calls, returns, and exceptions.

CRITICAL: A 'line' event fires BEFORE the line executes. This means the
variable state visible at a 'line' event at line N is the state AFTER
line N-1 finished, but BEFORE line N has started. We handle this by:

1. Recording state at each 'line' event (pre-execution state)
2. Comparing with previous state to detect what the PREVIOUS line changed
3. Attributing changes to the correct line in post-processing

This module can be used standalone (via trace_cli.py) or imported into
the sandbox runner for containerized execution.
"""

import copy
import io
import os
import sys
import traceback
from pathlib import Path
from typing import Any


# --- Safe variable copying ---

def safe_deepcopy(obj: Any, max_depth: int = 4, _depth: int = 0) -> Any:
    """
    Create a safe snapshot of a variable value.

    Handles: int, float, str, bool, None, list, tuple, set, dict.
    For unsupported types, returns a string representation.

    Depth-limited to prevent infinite recursion on self-referencing objects.
    """
    if _depth >= max_depth:
        return _safe_repr(obj)

    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        # Handle large ints and special floats without overflow
        if isinstance(obj, int) and (obj > 2**53 or obj < -(2**53)):
            return repr(obj)
        return obj
    if isinstance(obj, str):
        if len(obj) > 500:
            return obj[:500] + "...<truncated>"
        return obj
    if isinstance(obj, bytes):
        return f"<bytes: {len(obj)} bytes>"
    if isinstance(obj, (list, tuple)):
        if len(obj) > 50:
            truncated = [safe_deepcopy(v, max_depth, _depth + 1) for v in list(obj)[:50]]
            truncated.append(f"...<{len(obj) - 50} more items>")
            return truncated if isinstance(obj, list) else tuple(truncated)
        result = [safe_deepcopy(v, max_depth, _depth + 1) for v in obj]
        return result if isinstance(obj, list) else tuple(result)
    if isinstance(obj, set):
        if len(obj) > 50:
            items = [safe_deepcopy(v, max_depth, _depth + 1) for v in list(obj)[:50]]
            items.append(f"...<{len(obj) - 50} more items>")
            return items
        return [safe_deepcopy(v, max_depth, _depth + 1) for v in obj]
    if isinstance(obj, dict):
        if len(obj) > 50:
            result = {}
            for i, (k, v) in enumerate(obj.items()):
                if i >= 50:
                    result["...<truncated>"] = f"{len(obj) - 50} more keys"
                    break
                result[safe_deepcopy(k, max_depth, _depth + 1)] = safe_deepcopy(v, max_depth, _depth + 1)
            return result
        return {safe_deepcopy(k, max_depth, _depth + 1): safe_deepcopy(v, max_depth, _depth + 1) for k, v in obj.items()}
    # Unsupported type — return safe representation
    return _safe_repr(obj)


def _safe_repr(obj: Any) -> str:
    """Return a safe string representation, never crashing."""
    try:
        r = repr(obj)
        if len(r) > 200:
            return r[:200] + "..."
        return f"<{type(obj).__name__}: {r}>"
    except Exception:
        return f"<{type(obj).__name__} at {id(obj):#x}>"


# --- Output capture ---

class OutputCapture(io.StringIO):
    """
    A StringIO wrapper that records output in chunks along with
    the trace step that produced them.
    """

    def __init__(self):
        super().__init__()
        self.output_events: list[dict] = []  # {step, text} records

    def write(self, s: str) -> int:
        self.output_events.append({"text": s})
        return super().write(s)


# --- The tracer ---

class PythonTracer:
    """
    Traces execution of a Python script using sys.settrace().

    Usage:
        tracer = PythonTracer(source_path)
        tracer.run()

        # After run:
        print(tracer.to_json())
    """

    def __init__(self, source_path: Path, stdin_data: str = ""):
        self.source_path = source_path.resolve()
        self.source_path_str = str(self.source_path)
        self.stdin_data = stdin_data
        self.events: list[dict] = []
        self.step: int = 0
        self.prev_locals: dict[str, Any] = {}
        self.prev_line: int | None = None
        self.current_function: str = "<module>"
        self.stdout_capture = OutputCapture()
        self.stderr_capture = OutputCapture()
        self.exception_info: dict | None = None
        self._prev_stdout_len: int = 0
        self._prev_stderr_len: int = 0

    def _is_user_code(self, filename: str) -> bool:
        """
        Check whether a source filename belongs to the user's program.

        Uses os.path.samefile when possible (handles symlinks, relative
        vs absolute paths), falling back to string comparison.
        """
        try:
            return os.path.samefile(filename, self.source_path_str)
        except (OSError, FileNotFoundError):
            # One of the paths doesn't exist on disk (<string>, <stdin>, etc.)
            return filename == self.source_path_str

    def run(self) -> None:
        """Execute the source file under tracing."""
        # Prepare the source for execution
        source_code = self.source_path.read_text(encoding="utf-8")

        # Compile first to catch SyntaxErrors before tracing starts
        try:
            compiled = compile(source_code, self.source_path_str, "exec")
        except SyntaxError as e:
            self.exception_info = {
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text,
            }
            return

        # Set up stdin with user-provided input
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            if self.stdin_data:
                sys.stdin = io.StringIO(self.stdin_data)
            sys.stdout = self.stdout_capture
            sys.stderr = self.stderr_capture

            # Activate the trace hook
            sys.settrace(self._trace_fn)

            # Execute the compiled code in an isolated namespace
            exec_globals: dict[str, Any] = {"__name__": "__main__", "__file__": self.source_path}
            exec(compiled, exec_globals)

        except Exception:
            # Exception captured by trace_fn via 'exception' event
            pass
        finally:
            sys.settrace(None)
            sys.stdin = original_stdin
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def _trace_fn(self, frame, event: str, arg: Any) -> Any:
        """
        The trace function called by Python for every frame event.

        We filter aggressively: only trace frames whose source file matches
        the user's submitted program. Return None for everything else to
        prevent tracing into the standard library, the tracer itself, or
        the Python runtime.
        """
        # Filter: only trace the user's source file.
        # Use os.path.samefile to handle symlinks and relative vs absolute.
        if not self._is_user_code(frame.f_code.co_filename):
            return None

        if event == "call":
            self.current_function = frame.f_code.co_name
            return self._trace_fn

        elif event == "line":
            return self._handle_line(frame)

        elif event == "return":
            return self._handle_return(frame, arg)

        elif event == "exception":
            return self._handle_exception(frame, arg)

        return self._trace_fn

    def _handle_line(self, frame):
        """Handle a 'line' event — fires BEFORE the line executes."""
        self.step += 1
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name

        # Snapshot current locals (state AFTER previous line, BEFORE this line)
        current_locals = self._snapshot_locals(frame)

        # Detect changes since the previous step
        changes = self._compute_changes(self.prev_locals, current_locals)

        # Capture any output produced since the last event
        output = self._capture_output()

        self.events.append({
            "step": self.step,
            "event": "line",
            "line": lineno,
            "function": func_name,
            "changes": changes,
            "variables": current_locals,
            "output": output,
        })

        self.prev_locals = current_locals
        self.prev_line = lineno
        return self._trace_fn

    def _handle_return(self, frame, arg):
        """Handle a 'return' event."""
        self.step += 1
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name

        current_locals = self._snapshot_locals(frame)
        changes = self._compute_changes(self.prev_locals, current_locals)
        output = self._capture_output()

        self.events.append({
            "step": self.step,
            "event": "return",
            "line": lineno,
            "function": func_name,
            "changes": changes,
            "variables": current_locals,
            "output": output,
            "return_value": safe_deepcopy(arg),
        })

        self.prev_locals = current_locals
        return self._trace_fn

    def _handle_exception(self, frame, arg):
        """Handle an 'exception' event."""
        self.step += 1
        exc_type, exc_value, exc_tb = arg
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name

        current_locals = self._snapshot_locals(frame)
        output = self._capture_output()

        # Extract traceback frames from the user's source file only
        tb_frames = []
        tb = exc_tb
        while tb is not None:
            if self._is_user_code(tb.tb_frame.f_code.co_filename):
                tb_frames.append({
                    "file": tb.tb_frame.f_code.co_filename,
                    "line": tb.tb_lineno,
                    "function": tb.tb_frame.f_code.co_name,
                })
            tb = tb.tb_next

        self.exception_info = {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "line": lineno,
            "function": func_name,
            "traceback_frames": tb_frames,
        }

        self.events.append({
            "step": self.step,
            "event": "exception",
            "line": lineno,
            "function": func_name,
            "changes": {},
            "variables": current_locals,
            "output": output,
            "exception": self.exception_info,
        })

        self.prev_locals = current_locals
        # Don't continue tracing after an unhandled exception
        return None

    def _snapshot_locals(self, frame) -> dict[str, Any]:
        """
        Create a safe snapshot of local variables, excluding internal
        tracer variables and dunder names.
        """
        snapshot = {}
        for name, value in frame.f_locals.items():
            # Skip internal/tracer variables and dunder names
            if name.startswith("__") and name.endswith("__"):
                continue
            if name.startswith("_"):
                # Keep user's underscore variables, skip only if from tracer
                if name in ("_trace_fn", "_prev_locals", "_prev_line"):
                    continue
            # Skip reference to the tracer itself if it leaked
            if isinstance(value, PythonTracer):
                continue
            snapshot[name] = safe_deepcopy(value)
        return snapshot

    def _compute_changes(
        self,
        prev: dict[str, Any],
        curr: dict[str, Any],
    ) -> dict[str, dict]:
        """
        Compare previous and current local variable state.

        Returns a dict of variable_name -> change_info where change_info is:
          {"type": "created", "value": new_value}
          {"type": "updated", "old_value": ..., "new_value": ...}
          {"type": "deleted", "old_value": ...}
        """
        changes = {}
        all_names = set(prev.keys()) | set(curr.keys())

        for name in all_names:
            in_prev = name in prev
            in_curr = name in curr

            if not in_prev and in_curr:
                changes[name] = {"type": "created", "value": curr[name]}
            elif in_prev and not in_curr:
                changes[name] = {"type": "deleted", "old_value": prev[name]}
            elif in_prev and in_curr:
                # Both exist — check if value changed
                if prev[name] != curr[name]:
                    changes[name] = {
                        "type": "updated",
                        "old_value": prev[name],
                        "new_value": curr[name],
                    }

        return changes

    def _capture_output(self) -> str:
        """Capture stdout written since the last event."""
        full_stdout = self.stdout_capture.getvalue()
        new_output = full_stdout[self._prev_stdout_len:]
        self._prev_stdout_len = len(full_stdout)
        return new_output

    def to_dict(self) -> dict[str, Any]:
        """Return the complete trace result as a dictionary."""
        stdout = self.stdout_capture.getvalue()
        stderr = self.stderr_capture.getvalue()

        # Determine execution status
        if self.exception_info:
            if self.exception_info["type"] == "SyntaxError":
                status = "syntax_error"
            else:
                status = "runtime_error"
        else:
            status = "success"

        result: dict[str, Any] = {
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "timeline": self.events,
        }

        if self.exception_info:
            result["error"] = self.exception_info

        return result

    def to_json(self, indent: int = 2) -> str:
        """Return the complete trace result as pretty-printed JSON."""
        import json
        return json.dumps(self.to_dict(), indent=indent, default=str, ensure_ascii=False)
