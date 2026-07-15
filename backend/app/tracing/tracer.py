"""
CodeTrace AI — Python Runtime Tracer

Uses sys.settrace() to capture every execution event in a user's Python
program: line execution, function calls, returns, and exceptions.

CRITICAL: A 'line' event fires BEFORE the line executes. This means the
variable state visible at a 'line' event at line N is the state AFTER
line N-1 finished, but BEFORE line N has started. We handle this by:

1. Recording state at each 'line' event (pre-execution state)
2. Comparing with previous state to detect what the PREVIOUS line changed
3. Attributing changes to the correct line in post-processing (TraceProcessor)

This module can be used standalone (via trace_cli.py) or imported into
the sandbox runner for containerized execution.
"""

import io
import os
import sys
from pathlib import Path
from typing import Any

from .serializer import TraceSerializer
from .state_tracker import StateTracker
from .trace_processor import TraceProcessor


class OutputCapture(io.StringIO):
    """
    A StringIO wrapper that records output in chunks along with
    the trace step that produced them.
    """

    def __init__(self):
        super().__init__()
        self.output_events: list[dict] = []

    def write(self, s: str) -> int:
        self.output_events.append({"text": s})
        return super().write(s)


class PythonTracer:
    """
    Traces execution of a Python script using sys.settrace().

    Usage:
        tracer = PythonTracer(source_path)
        tracer.run()

        # Raw events (before processing):
        print(tracer.raw_events)

        # Processed timeline:
        print(tracer.get_timeline())
    """

    def __init__(
        self,
        source_path: Path,
        stdin_data: str = "",
        serializer: TraceSerializer | None = None,
        state_tracker: StateTracker | None = None,
        trace_processor: TraceProcessor | None = None,
    ):
        self.source_path = source_path.resolve()
        self.source_path_str = str(self.source_path)
        self.stdin_data = stdin_data

        # Components (can be injected for testing)
        self._serializer = serializer or TraceSerializer()
        self._state_tracker = state_tracker or StateTracker()
        self._trace_processor = trace_processor or TraceProcessor()

        # Execution state
        self.raw_events: list[dict] = []
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
            return filename == self.source_path_str

    def run(self) -> None:
        """Execute the source file under tracing."""
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

        # Set up I/O redirection
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            if self.stdin_data:
                sys.stdin = io.StringIO(self.stdin_data)
            sys.stdout = self.stdout_capture
            sys.stderr = self.stderr_capture

            sys.settrace(self._trace_fn)

            exec_globals: dict[str, Any] = {
                "__name__": "__main__",
                "__file__": self.source_path_str,
            }
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

        current_locals = self._serializer.serialize_locals(frame.f_locals)
        changes = self._state_tracker.compare(self.prev_locals, current_locals)
        output = self._capture_output()

        self.raw_events.append({
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

        current_locals = self._serializer.serialize_locals(frame.f_locals)
        changes = self._state_tracker.compare(self.prev_locals, current_locals)
        output = self._capture_output()

        self.raw_events.append({
            "step": self.step,
            "event": "return",
            "line": lineno,
            "function": func_name,
            "changes": changes,
            "variables": current_locals,
            "output": output,
            "return_value": self._serializer.serialize(arg),
        })

        self.prev_locals = current_locals
        return self._trace_fn

    def _handle_exception(self, frame, arg):
        """Handle an 'exception' event."""
        self.step += 1
        exc_type, exc_value, exc_tb = arg
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name

        current_locals = self._serializer.serialize_locals(frame.f_locals)
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

        self.raw_events.append({
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
        return None  # Stop tracing after unhandled exception

    def _capture_output(self) -> str:
        """Capture stdout written since the last event."""
        full_stdout = self.stdout_capture.getvalue()
        new_output = full_stdout[self._prev_stdout_len:]
        self._prev_stdout_len = len(full_stdout)
        return new_output

    def get_timeline(self) -> list[dict[str, Any]]:
        """Return the processed (clean) timeline."""
        return self._trace_processor.process(self.raw_events)

    def to_dict(self) -> dict[str, Any]:
        """Return the complete trace result as a dictionary."""
        stdout = self.stdout_capture.getvalue()
        stderr = self.stderr_capture.getvalue()

        if self.exception_info:
            status = "syntax_error" if self.exception_info["type"] == "SyntaxError" else "runtime_error"
        else:
            status = "success"

        result: dict[str, Any] = {
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "timeline": self.get_timeline(),
        }

        if self.exception_info:
            result["error"] = self.exception_info

        return result

    def to_json(self, indent: int = 2) -> str:
        """Return the complete trace result as pretty-printed JSON."""
        import json
        return json.dumps(self.to_dict(), indent=indent, default=str, ensure_ascii=False)
