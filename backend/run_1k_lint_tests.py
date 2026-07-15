#!/usr/bin/env python3
"""
CodeTrace Live Fix — 1000 File Bulk Lint Test

Generates 1000 Python programs (10–1000 lines) with a mix of:
- Clean code (no diagnostics expected)
- Buggy code (F821, F401, F811, F823, B rules, syntax errors)

Runs each through POST /api/lint and reports accuracy.
"""

import json
import random
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "http://localhost:8000/api/lint"

# ── Generators ────────────────────────────────────────────────────────────

def gen_clean(lines: int) -> str:
    """Generate valid Python code that should have zero lint issues."""
    code = []
    for i in range(lines):
        choice = random.random()
        if choice < 0.3:
            code.append(f"x_{i} = {random.randint(1, 100)}")
        elif choice < 0.5:
            code.append(f"print(x_{i % max(1, i)})")
        elif choice < 0.7:
            code.append(f"# comment line {i}")
        elif choice < 0.9:
            code.append(f"y_{i} = x_{i % max(1, i)} + {random.randint(1, 10)}")
        else:
            code.append("")  # blank line
    return "\n".join(code) + "\n"


def gen_f821(lines: int) -> str:
    """Generate code with an undefined name somewhere."""
    code = [f"known_var_{i} = {i}" for i in range(max(1, lines // 3))]
    insert_line = random.randint(1, max(1, len(code) - 1))
    code.insert(insert_line, "print(unknown_typo_var)")
    # Fill rest with valid lines
    while len(code) < lines:
        code.append(f"x_{len(code)} = {len(code)}")
    return "\n".join(code[:lines]) + "\n"


def gen_f401(lines: int) -> str:
    """Generate code with an unused import."""
    unused = random.choice(["os", "sys", "json", "math", "re", "datetime"])
    code = [f"import {unused}"]
    code.append(f"used_var = 42")
    for i in range(2, lines):
        code.append(f"print({i % 10})")
    return "\n".join(code[:lines]) + "\n"


def gen_mixed(lines: int) -> str:
    """Generate code with multiple intentional issues."""
    issues = random.sample(["f821", "f401", "syntax", "clean"], k=min(2, lines // 20 + 1))
    code = []
    for issue in issues:
        if issue == "f821":
            code.append("print(nonexistent_var)")
        elif issue == "f401":
            code.append("import collections")
        elif issue == "syntax":
            code.append("if True\n    pass")
        else:
            code.append("x = 1")
    while len(code) < lines:
        code.append(f"v_{len(code)} = {len(code)}")
    return "\n".join(code[:lines]) + "\n"


def gen_syntax_error(lines: int) -> str:
    """Generate code with a syntax error."""
    code = [f"x_{i} = {i}" for i in range(lines - 1)]
    code.insert(random.randint(0, max(0, len(code) - 1)), "if x > 5\n    print('missing colon above')")
    return "\n".join(code[:lines]) + "\n"


# ── Test distribution ──────────────────────────────────────────────────────

LINE_BUCKETS = [10, 25, 50, 100, 200, 350, 500, 750, 1000]
GENERATORS = [
    (gen_clean, 400),       # 40% clean
    (gen_f821, 200),        # 20% undefined name
    (gen_f401, 150),        # 15% unused import
    (gen_mixed, 150),       # 15% mixed bugs
    (gen_syntax_error, 100), # 10% syntax errors
]
TOTAL = sum(n for _, n in GENERATORS)


def generate_all():
    tests = []
    for gen_fn, count in GENERATORS:
        for _ in range(count):
            lines = random.choice(LINE_BUCKETS)
            code = gen_fn(lines)
            expected = "clean" if gen_fn is gen_clean else "issues"
            if gen_fn is gen_syntax_error:
                expected = "syntax"
            tests.append({"code": code, "expected": expected, "lines": len(code.split("\n"))})
    random.shuffle(tests)
    return tests


def run_one(test):
    try:
        data = json.dumps({"code": test["code"]}).encode()
        req = urllib.request.Request(API, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        diags = result.get("diagnostics", [])
        errors = [d for d in diags if d["severity"] == "error"]
        warnings = [d for d in diags if d["severity"] == "warning"]

        # Check for W292 or other style codes
        style_codes = [d["code"] for d in diags if d["code"] in ("W292", "E501", "W291", "W293", "W391")]
        has_style = len(style_codes) > 0

        # Determine if this was correctly classified
        has_issues = len(errors) + len(warnings) > 0
        if test["expected"] == "clean":
            correct = not has_issues
        elif test["expected"] == "syntax":
            correct = any("Syntax" in d.get("code", "") or d.get("code", "").startswith("E") for d in diags)
        else:
            correct = has_issues

        return {
            "lines": test["lines"],
            "expected": test["expected"],
            "has_errors": len(errors) > 0,
            "has_warnings": len(warnings) > 0,
            "total_diags": len(diags),
            "has_style": has_style,
            "style_codes": style_codes,
            "correct": correct,
            "error": None,
        }
    except Exception as e:
        return {
            "lines": test["lines"],
            "expected": test["expected"],
            "error": str(e)[:100],
            "correct": False,
        }


def main():
    print(f"Generating {TOTAL} test programs (10–1000 lines)...")
    tests = generate_all()
    print(f"Generated {len(tests)} tests")
    print(f"Running with 8 threads...\n")

    results = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(run_one, t): i for i, t in enumerate(tests)}
        for future in as_completed(futures):
            results.append(future.result())
            if len(results) % 100 == 0:
                elapsed = time.time() - start
                rate = len(results) / elapsed
                eta = (TOTAL - len(results)) / rate
                print(f"  {len(results)}/{TOTAL} ({rate:.0f}/s, ETA {eta:.0f}s)")

    total_time = time.time() - start
    print(f"\nCompleted in {total_time:.1f}s ({len(results)/total_time:.0f}/s)\n")

    # Analysis
    errors = [r for r in results if r.get("error")]
    no_errors = [r for r in results if not r.get("error")]
    correct = [r for r in no_errors if r["correct"]]
    incorrect = [r for r in no_errors if not r["correct"]]
    style_leaks = [r for r in no_errors if r.get("has_style")]

    # By line bucket
    line_buckets = Counter()
    line_correct = Counter()
    for r in no_errors:
        for b in LINE_BUCKETS:
            if r["lines"] <= b:
                line_buckets[b] += 1
                if r["correct"]:
                    line_correct[b] += 1
                break

    print("=" * 70)
    print("  CodeTrace Live Fix — 1K File Lint Test Report")
    print("=" * 70)
    print()
    print(f"  Total tests:        {len(results)}")
    print(f"  Runner errors:      {len(errors)}")
    print(f"  Style leaks (W292): {len(style_leaks)}")
    print(f"  Correct:            {len(correct)}/{len(no_errors)} ({len(correct)/max(len(no_errors),1)*100:.1f}%)")
    print(f"  Throughput:         {len(results)/total_time:.0f} tests/s")
    print()

    # Status breakdown
    print("─" * 70)
    print("  EXPECTED VS ACTUAL")
    print("─" * 70)
    for exp in ["clean", "issues", "syntax"]:
        subset = [r for r in no_errors if r["expected"] == exp]
        if subset:
            acc = sum(1 for r in subset if r["correct"]) / len(subset) * 100
            print(f"  {exp:<10} {len(subset):>5} tests  accuracy: {acc:.1f}%")
    print()

    # Line size performance
    print("─" * 70)
    print("  ACCURACY BY CODE SIZE")
    print("─" * 70)
    for b in LINE_BUCKETS:
        total = line_buckets[b]
        corr = line_correct[b]
        if total > 0:
            bar = "█" * int(corr / total * 30)
            print(f"  ≤{b:>4} lines  {corr:>4}/{total:<4}  {corr/total*100:.0f}%  {bar}")
    print()

    # Diagnostic breakdown
    diag_codes = Counter()
    for r in no_errors:
        for code in r.get("style_codes", []):
            diag_codes[code] += 1
    if diag_codes:
        print("─" * 70)
        print("  STYLE DIAGNOSTIC BREAKDOWN (should be empty)")
        print("─" * 70)
        for code, count in diag_codes.most_common():
            print(f"  {code}: {count}")

    # Show sample incorrect results
    if incorrect:
        print()
        print(f"─" * 70)
        print(f"  INCORRECT RESULTS ({len(incorrect)} total — showing first 5)")
        print("─" * 70)
        for r in incorrect[:5]:
            print(f"  Expected: {r['expected']}, Lines: {r['lines']}, "
                  f"Errors: {r.get('has_errors')}, Warnings: {r.get('has_warnings')}, "
                  f"Diags: {r.get('total_diags')}, Style: {r.get('has_style')}")

    print()
    print("=" * 70)
    acc = len(correct) / max(len(no_errors), 1) * 100
    print(f"  OVERALL ACCURACY: {acc:.1f}%")
    print(f"  STYLE LEAKS: {len(style_leaks)} (should be 0)")
    print("=" * 70)


if __name__ == "__main__":
    main()
