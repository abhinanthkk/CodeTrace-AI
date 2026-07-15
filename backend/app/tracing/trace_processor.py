"""
CodeTrace AI — Trace Processor

Post-processes raw sys.settrace() events into a clean execution timeline
suitable for the frontend.

Key responsibilities:
1. Filter out no-op steps (nothing changed, no output, not important)
2. Attribute variable changes to the correct source line
   (since 'line' fires BEFORE execution, changes belong to the PREVIOUS line)
3. Merge consecutive output into the correct step
4. Ensure step numbers remain sequential
5. Limit timeline size to prevent huge responses
"""

from typing import Any

# Maximum timeline steps returned to the frontend
MAX_TIMELINE_STEPS = 500


class TraceProcessor:
    """
    Processes raw trace events into a clean, frontend-ready timeline.

    Usage:
        processor = TraceProcessor()
        raw_events = tracer.events
        timeline = processor.process(raw_events)
    """

    def process(self, raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Transform raw trace events into a processed timeline.

        Processing steps:
        1. Attribute changes to the line that caused them (previous line)
        2. Filter out steps with no meaningful change (unless important event)
        3. Re-number steps sequentially
        4. Truncate if over MAX_TIMELINE_STEPS
        """
        if not raw_events:
            return []

        # Step 1: Attribute changes to the correct line
        attributed = self._attribute_changes(raw_events)

        # Step 2: Filter noise
        filtered = self._filter_noise(attributed)

        # Step 3: Re-number
        for i, step in enumerate(filtered, start=1):
            step["step"] = i

        # Step 4: Truncate if needed
        if len(filtered) > MAX_TIMELINE_STEPS:
            filtered = filtered[:MAX_TIMELINE_STEPS]
            filtered.append({
                "step": len(filtered) + 1,
                "event": "system",
                "line": 0,
                "function": "",
                "changes": {},
                "variables": {},
                "output": f"...<timeline truncated at {MAX_TIMELINE_STEPS} steps>",
            })

        return filtered

    def _attribute_changes(
        self, events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Attribute variable changes to the line that actually caused them.

        sys.settrace() fires 'line' events BEFORE the line executes. So when
        we get a 'line' event at line N, the variable changes we detect are
        the result of the PREVIOUS line (or event) having just finished.

        Example:
          Raw: line 1 (state={}), line 3 (state={arr created})
          Fixed: line 1 (arr created) — arr was created by executing line 1

        Strategy: each 'line' event at line N gets re-labeled to the
        previously-seen line number, because that's the line that just
        finished executing and caused the state change.

        Exception events keep their actual line (the exception happened there).
        The first event keeps its line (nothing executed before it).
        """
        if not events:
            return []

        result: list[dict[str, Any]] = []
        prev_event_line: int | None = None

        for event in events:
            fixed = dict(event)

            if event["event"] == "line":
                if prev_event_line is not None:
                    # This 'line' event at line N means the code at
                    # prev_event_line just finished. Attribute changes there.
                    fixed["line"] = prev_event_line
                # else: first event — keep its line as-is

            prev_event_line = event["line"]

            # Exception events keep their actual line (the crash line)
            if event["event"] == "exception":
                fixed["line"] = event["line"]

            result.append(fixed)

        return result

    def _filter_noise(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Remove steps that add no meaningful information.

        Kept:
        - Steps with variable changes
        - Steps with output
        - Function calls
        - Returns
        - Exceptions

        Removed:
        - Line events with no changes and no output (empty steps)
          UNLESS they are the first step or the only step on that line.
        """
        if not events:
            return []

        # Track which lines have been seen to avoid removing the only event
        # for a line (which would make it seem like the line never executed)
        line_counts: dict[int, int] = {}
        for e in events:
            if e["event"] == "line":
                line_counts[e["line"]] = line_counts.get(e["line"], 0) + 1

        filtered: list[dict[str, Any]] = []
        for event in events:
            if self._is_important(event, line_counts):
                filtered.append(event)

        return filtered

    def _is_important(
        self, event: dict[str, Any], line_counts: dict[int, int]
    ) -> bool:
        """Determine whether a trace event is meaningful enough to show."""
        # Always keep: call, return, exception, system
        if event["event"] in ("call", "return", "exception", "system"):
            return True

        # Keep if there are variable changes
        if event.get("changes"):
            return True

        # Keep if there is output
        if event.get("output", "").strip():
            return True

        # Keep if this is the only event for this line (don't lose coverage)
        if event["event"] == "line" and line_counts.get(event["line"], 0) <= 1:
            return True

        return False

    def to_summary(self, timeline: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate a summary of the timeline for logging/debugging."""
        total_steps = len(timeline)
        error_step = None
        variable_count = 0

        for step in timeline:
            if step["event"] == "exception":
                error_step = step["step"]
            variable_count = max(variable_count, len(step.get("variables", {})))

        return {
            "total_steps": total_steps,
            "error_step": error_step,
            "max_variables": variable_count,
        }
