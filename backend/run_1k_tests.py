#!/usr/bin/env python3
"""
CodeTrace AI — 1000 Demo Files Bulk Test Runner

Generates 1000 diverse Python programs (mix of correct and buggy),
executes each through the tracer, and produces an analysis table.
"""

import json
import os
import random
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.tracing.tracer import PythonTracer
from app.analysis.analyzer import analyze_failure

# ─── Test program generators ────────────────────────────────────────────

def gen_success(i: int) -> tuple[str, str, str]:
    """Correct programs — various patterns."""
    patterns = [
        # Basic arithmetic
        (f"# Test {i}: basic math\nx = {i % 100}\ny = {i % 50 + 1}\nz = x + y\nprint(z)\n", ""),
        # String manipulation
        (f"# Test {i}: strings\nname = 'user_{i}'\ngreeting = f'Hello {{name}}'\nprint(greeting)\n", ""),
        # List operations
        (f"# Test {i}: lists\ndata = [1, 2, 3, 4, 5]\ntotal = sum(data)\nprint(total)\n", ""),
        # Conditional logic
        (f"# Test {i}: conditional\nx = {i % 100}\nif x > 50:\n    print('high')\nelse:\n    print('low')\n", ""),
        # Loop with safe range
        (f"# Test {i}: safe loop\nresult = 0\nfor j in range({(i % 5) + 3}):\n    result += j\nprint(result)\n", ""),
        # Dict operations
        (f"# Test {i}: dict\nd = {{'a': 1, 'b': 2}}\nprint(d.get('a', 0))\n", ""),
        # Multiple variables
        (f"# Test {i}: multi var\na = 1\nb = 2\nc = a + b\nd = c * 2\nprint(d)\n", ""),
        # Input simulation
        (f"# Test {i}: no crash\nx = 42\nprint(f'Value: {{x}}')\n", ""),
    ]
    code, stdin_data = random.choice(patterns)
    return code, stdin_data, "success"


def gen_index_error(i: int) -> tuple[str, str, str]:
    """IndexError programs."""
    patterns = [
        f"# Test {i}: out of bounds\narr = [10, 20, 30]\nfor j in range(4):\n    print(arr[j])\n",
        f"# Test {i}: empty list\nempty = []\nprint(empty[0])\n",
        f"# Test {i}: negative index\nnums = [1, 2, 3]\nprint(nums[-4])\n",
        f"# Test {i}: string index\ns = 'hi'\nprint(s[5])\n",
    ]
    return random.choice(patterns), "", "index_error"


def gen_zero_division(i: int) -> tuple[str, str, str]:
    """ZeroDivisionError programs."""
    patterns = [
        f"# Test {i}: div by zero\nx = {i % 10}\ny = 0\nresult = x / y\n",
        f"# Test {i}: modulo zero\na = 10\nb = 0\nc = a % b\n",
    ]
    return random.choice(patterns), "", "zero_division"


def gen_key_error(i: int) -> tuple[str, str, str]:
    """KeyError programs."""
    patterns = [
        f"# Test {i}: missing key\nd = {{'name': 'test'}}\nprint(d['age'])\n",
        f"# Test {i}: empty dict\nd = {{}}\nprint(d['key'])\n",
    ]
    return random.choice(patterns), "", "key_error"


def gen_name_error(i: int) -> tuple[str, str, str]:
    """NameError programs."""
    patterns = [
        f"# Test {i}: typo\nuserName = 'test'\nprint(username)\n",
        f"# Test {i}: undefined\nx = 10\nprint(y)\n",
        f"# Test {i}: misspelled\ncounter = 0\nprint(countre)\n",
    ]
    return random.choice(patterns), "", "name_error"


def gen_type_error(i: int) -> tuple[str, str, str]:
    """TypeError programs."""
    patterns = [
        f"# Test {i}: str + int\nage = {20 + i % 30}\nmsg = 'Age: ' + age\n",
        f"# Test {i}: int call\nx = 5\nx()\n",
        f"# Test {i}: None op\nval = None\nprint(val + 1)\n",
    ]
    return random.choice(patterns), "", "type_error"


def gen_syntax_error(i: int) -> tuple[str, str, str]:
    """SyntaxError programs."""
    patterns = [
        f"# Test {i}: missing colon\nx = 10\nif x > 5\n    print(x)\n",
        f"# Test {i}: bad indent\nx = 10\n print(x)\n",
        f"# Test {i}: missing paren\nprint 'hello'\n",
    ]
    return random.choice(patterns), "", "syntax_error"


def gen_with_input(i: int) -> tuple[str, str, str]:
    """Programs using input()."""
    name = f"user_{i % 100}"
    age = str(20 + i % 50)
    return (
        f"# Test {i}: input\nname = input()\nage = int(input())\nprint(f'{{name}} is {{age}}')\n",
        f"{name}\n{age}\n",
        "input_expected_success",
    )


# ─── Test distribution ───────────────────────────────────────────────────

GENERATORS = [
    (gen_success, 420),         # 42% correct
    (gen_index_error, 150),     # 15% IndexError
    (gen_zero_division, 80),    #  8% ZeroDivisionError
    (gen_key_error, 80),        #  8% KeyError
    (gen_name_error, 80),       #  8% NameError
    (gen_type_error, 80),       #  8% TypeError
    (gen_syntax_error, 50),     #  5% SyntaxError
    (gen_with_input, 60),       #  6% input programs
]

TOTAL = sum(n for _, n in GENERATORS)


def generate_all() -> list[tuple[int, str, str, str]]:
    """Generate all test programs with their expected categories."""
    tests = []
    idx = 0
    for gen_fn, count in GENERATORS:
        for _ in range(count):
            code, stdin_data, expected = gen_fn(idx)
            tests.append((idx, code, stdin_data, expected))
            idx += 1
    random.shuffle(tests)
    return tests


def run_one(test: tuple[int, str, str, str]) -> dict:
    """Execute a single test and return results."""
    idx, code, stdin_data, expected = test

    result = {
        "id": idx,
        "expected": expected,
        "code_len": len(code),
        "input_len": len(stdin_data),
        "status": "unknown",
        "error_type": None,
        "error_line": None,
        "analysis_category": None,
        "analysis_confidence": None,
        "timeline_steps": 0,
        "duration_ms": 0,
        "match_expected": False,
        "stdout_len": 0,
        "stderr_len": 0,
    }

    start = time.time()

    try:
        # Write code to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = Path(f.name)

        tracer = PythonTracer(tmp_path, stdin_data=stdin_data)
        tracer.run()
        trace_result = tracer.to_dict()

        result["duration_ms"] = round((time.time() - start) * 1000, 1)
        result["status"] = trace_result["status"]
        result["stdout_len"] = len(trace_result.get("stdout", ""))
        result["stderr_len"] = len(trace_result.get("stderr", ""))
        result["timeline_steps"] = len(trace_result.get("timeline", []))

        if trace_result.get("error"):
            err = trace_result["error"]
            result["error_type"] = err.get("type")
            result["error_line"] = err.get("line")

            # Run analysis
            analysis = analyze_failure(err, trace_result.get("timeline", []))
            if analysis:
                result["analysis_category"] = analysis.get("category")
                result["analysis_confidence"] = analysis.get("confidence")

        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    except Exception as e:
        result["status"] = "runner_error"
        result["error_type"] = type(e).__name__
        result["duration_ms"] = round((time.time() - start) * 1000, 1)

    # Match against expected
    result["match_expected"] = _check_match(result["status"], result["error_type"], result["analysis_category"], expected)

    return result


def _check_match(status: str, error_type: str | None, analysis: str | None, expected: str) -> bool:
    """Check if result matches expected category."""
    if expected == "success":
        return status == "success"
    if expected == "index_error":
        return status == "runtime_error" and error_type == "IndexError" and analysis == "index_out_of_range"
    if expected == "zero_division":
        return status == "runtime_error" and error_type == "ZeroDivisionError" and analysis == "division_by_zero"
    if expected == "key_error":
        return status == "runtime_error" and error_type == "KeyError" and analysis == "key_not_found"
    if expected == "name_error":
        return status == "runtime_error" and error_type == "NameError" and analysis == "name_not_defined"
    if expected == "type_error":
        return status == "runtime_error" and error_type == "TypeError" and analysis == "type_mismatch"
    if expected == "syntax_error":
        return status == "syntax_error"
    if expected == "input_expected_success":
        return status == "success"
    return False


# ─── Main ────────────────────────────────────────────────────────────────

def main():
    print(f"Generating {TOTAL} test programs...")
    tests = generate_all()
    print(f"Generated {len(tests)} tests")
    print(f"Running with {os.cpu_count() or 4} workers...\n")

    results = []
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 8)) as executor:
        futures = {executor.submit(run_one, t): t[0] for t in tests}
        completed = 0
        for future in as_completed(futures):
            results.append(future.result())
            completed += 1
            if completed % 100 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                eta = (TOTAL - completed) / rate
                print(f"  {completed}/{TOTAL} completed ({rate:.0f}/s, ETA {eta:.0f}s)")

    total_time = time.time() - start_time
    print(f"\nCompleted {len(results)} tests in {total_time:.1f}s ({len(results)/total_time:.0f}/s)\n")

    # ─── Analysis ─────────────────────────────────────────────────────────
    print_analysis(results, total_time)


def print_analysis(results: list[dict], total_time: float):
    """Print the analysis table."""

    # Status distribution
    status_counts = Counter(r["status"] for r in results)
    error_type_counts = Counter(r["error_type"] for r in results if r["error_type"])
    analysis_counts = Counter(r["analysis_category"] for r in results if r["analysis_category"])

    # Match statistics
    matches = sum(1 for r in results if r["match_expected"])
    mismatches = [r for r in results if not r["match_expected"]]

    # Timing
    durations = [r["duration_ms"] for r in results]
    avg_ms = sum(durations) / len(durations) if durations else 0

    # Timeline stats
    steps = [r["timeline_steps"] for r in results if r["timeline_steps"] > 0]
    avg_steps = sum(steps) / len(steps) if steps else 0

    # Confidence stats
    confidences = [r["analysis_confidence"] for r in results if r["analysis_confidence"] is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    print("=" * 85)
    print("  CodeTrace AI — 1000 Demo Files Test Report")
    print("=" * 85)
    print()

    # ─── Table 1: Overall Summary ───
    print("┌──────────────────────────────────────────────────────────────────────────┐")
    print("│                          EXECUTION SUMMARY                               │")
    print("├────────────────────────────┬─────────────────────────────────────────────┤")
    print(f"│ Total tests                │ {len(results):>6}                                   │")
    print(f"│ Total execution time       │ {total_time:>6.1f}s                                  │")
    print(f"│ Throughput                 │ {len(results)/total_time:>6.0f} tests/s                            │")
    print(f"│ Avg execution time         │ {avg_ms:>6.1f} ms                                │")
    print(f"│ Avg timeline steps         │ {avg_steps:>6.1f}                                  │")
    print(f"│ Avg confidence (analyzers) │ {avg_confidence:>6.2f}                                  │")
    print("└────────────────────────────┴─────────────────────────────────────────────┘")
    print()

    # ─── Table 2: Status Distribution ───
    print("┌──────────────────────────────────────────────────────────────────────────┐")
    print("│                       EXECUTION STATUS DISTRIBUTION                      │")
    print("├────────────────────────────┬──────────┬────────────┬─────────────────────┤")
    print("│ Status                     │ Count    │ Percentage │ Bar                 │")
    print("├────────────────────────────┼──────────┼────────────┼─────────────────────┤")
    for status, label in [
        ("success", "Success"),
        ("runtime_error", "Runtime Error"),
        ("syntax_error", "Syntax Error"),
        ("runner_error", "Runner Error"),
    ]:
        count = status_counts.get(status, 0)
        pct = count / len(results) * 100
        bar = "█" * int(pct / 2)
        print(f"│ {label:<27}│ {count:>6}   │ {pct:>5.1f}%    │ {bar:<20}│")
    print("└────────────────────────────┴──────────┴────────────┴─────────────────────┘")
    print()

    # ─── Table 3: Error Type Breakdown ───
    print("┌──────────────────────────────────────────────────────────────────────────┐")
    print("│                         ERROR TYPE BREAKDOWN                             │")
    print("├────────────────────────────┬──────────┬────────────┬─────────────────────┤")
    print("│ Error Type                 │ Count    │ Percentage │ Bar                 │")
    print("├────────────────────────────┼──────────┼────────────┼─────────────────────┤")
    total_errors = sum(error_type_counts.values())
    for err_type in ["IndexError", "ZeroDivisionError", "KeyError", "NameError", "TypeError", "SyntaxError", "Other"]:
        if err_type == "Other":
            count = total_errors - sum(error_type_counts.get(t, 0) for t in ["IndexError", "ZeroDivisionError", "KeyError", "NameError", "TypeError", "SyntaxError"])
        else:
            count = error_type_counts.get(err_type, 0)
        if count > 0:
            pct = count / max(total_errors, 1) * 100
            bar = "█" * int(pct / 2)
            print(f"│ {err_type:<27}│ {count:>6}   │ {pct:>5.1f}%    │ {bar:<20}│")
    print("└────────────────────────────┴──────────┴────────────┴─────────────────────┘")
    print()

    # ─── Table 4: Analyzer Performance ───
    print("┌──────────────────────────────────────────────────────────────────────────┐")
    print("│                       ANALYZER PERFORMANCE                               │")
    print("├────────────────────────────┬──────────┬──────────┬──────────┬────────────┤")
    print("│ Analyzer Category          │ Count    │ Avg Conf │ Accuracy │ Status     │")
    print("├────────────────────────────┼──────────┼──────────┼──────────┼────────────┤")

    # Calculate per-category accuracy
    for cat, cat_label in [
        ("index_out_of_range", "IndexError Analyzer"),
        ("division_by_zero", "ZeroDivision Analyzer"),
        ("key_not_found", "KeyError Analyzer"),
        ("name_not_defined", "NameError Analyzer"),
        ("type_mismatch", "TypeError Analyzer"),
    ]:
        cat_results = [r for r in results if r["analysis_category"] == cat]
        if cat_results:
            count = len(cat_results)
            confs = [r["analysis_confidence"] for r in cat_results if r["analysis_confidence"] is not None]
            avg_c = sum(confs) / len(confs) if confs else 0
            accurate = sum(1 for r in cat_results if r["match_expected"])
            acc_pct = accurate / count * 100
            status = "✓ PASS" if acc_pct >= 90 else "⚠ WARN" if acc_pct >= 70 else "✗ FAIL"
            print(f"│ {cat_label:<27}│ {count:>6}   │ {avg_c:>6.2f}  │ {acc_pct:>6.1f}%  │ {status:<10} │")

    # Unknown/generic
    unknown = [r for r in results if r["analysis_category"] == "unknown"]
    if unknown:
        print(f"│ {'Generic (unknown)':<27}│ {len(unknown):>6}   │ {'N/A':>6}  │ {'N/A':>6}  │ {'—':<10} │")

    print("└────────────────────────────┴──────────┴──────────┴──────────┴────────────┘")
    print()

    # ─── Table 5: Match Accuracy by Expected Category ───
    print("┌──────────────────────────────────────────────────────────────────────────┐")
    print("│                     MATCH ACCURACY BY CATEGORY                            │")
    print("├────────────────────────────┬──────────┬──────────┬────────────────────────┤")
    print("│ Expected Category          │ Count    │ Accuracy │ Status                 │")
    print("├────────────────────────────┼──────────┼──────────┼────────────────────────┤")
    expected_categories = Counter(r["expected"] for r in results)
    for exp, label in [
        ("success", "Correct programs"),
        ("index_error", "IndexError"),
        ("zero_division", "ZeroDivisionError"),
        ("key_error", "KeyError"),
        ("name_error", "NameError"),
        ("type_error", "TypeError"),
        ("syntax_error", "SyntaxError"),
        ("input_expected_success", "Input programs"),
    ]:
        total_in_cat = expected_categories.get(exp, 0)
        if total_in_cat > 0:
            matched = sum(1 for r in results if r["expected"] == exp and r["match_expected"])
            acc = matched / total_in_cat * 100
            status = "✓" if acc >= 95 else "⚠" if acc >= 80 else "✗"
            print(f"│ {label:<27}│ {total_in_cat:>6}   │ {acc:>6.1f}%  │ {status:<22} │")
    print("└────────────────────────────┴──────────┴──────────┴────────────────────────┘")
    print()

    # ─── Table 6: Mismatches ───
    if mismatches:
        print(f"┌──────────────────────────────────────────────────────────────────────────┐")
        print(f"│ MISMATCHED RESULTS ({len(mismatches)} total)                                              │")
        print(f"├──────┬────────────────────┬────────────────────┬─────────────────────────┤")
        print(f"│ ID   │ Expected           │ Got                │ Details                 │")
        print(f"├──────┼────────────────────┼────────────────────┼─────────────────────────┤")
        for r in mismatches[:20]:
            exp = r["expected"][:18]
            got = f"{r['status']}"
            if r.get("error_type"):
                got += f"/{r['error_type']}"
            got = got[:18]
            detail = f"analysis={r.get('analysis_category','none')}"
            print(f"│ {r['id']:<4} │ {exp:<18} │ {got:<18} │ {detail:<23} │")
        if len(mismatches) > 20:
            print(f"│ ...  │ ...                │ ...                │ ({len(mismatches)-20} more)              │")
        print(f"└──────┴────────────────────┴────────────────────┴─────────────────────────┘")

    print()
    print("=" * 85)
    overall_acc = matches / len(results) * 100
    print(f"  OVERALL ACCURACY: {overall_acc:.1f}% ({matches}/{len(results)} matched expected)")
    print("=" * 85)


if __name__ == "__main__":
    main()
