"""Formats and saves evaluation results, including per-test-case scores."""

import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
from typing import List, Dict, Any


def generate_junit_xml(results: List[Dict[str, Any]], output_xml: str = "unit.xml") -> None:
    """Writes results in JUnit-style XML, for platforms that parse test
    results as a JUnit report rather than a CSV.

    Each test case becomes a <testcase>, grouped under a single <testsuite>.
    A failing case gets a <failure> element containing the reason. The 0-10
    score is attached as a JUnit "property" on each test case (a common,
    widely-supported extension point) since plain JUnit XML has no native
    concept of a partial score alongside pass/fail.
    """
    total = len(results)
    failures = sum(1 for r in results if not r["passed"])

    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ShopEase Chatbot Eval Suite",
            "tests": str(total),
            "failures": str(failures),
            "errors": "0",
            "skipped": "0",
        },
    )

    for r in results:
        testcase = ET.SubElement(
            testsuite,
            "testcase",
            {
                "classname": r["category"],
                "name": r["id"],
                "time": "0",
            },
        )

        properties = ET.SubElement(testcase, "properties")
        ET.SubElement(
            properties,
            "property",
            {"name": "score", "value": str(r.get("score", 0.0))},
        )
        ET.SubElement(
            properties,
            "property",
            {"name": "eval_method", "value": str(r.get("eval_method", ""))},
        )

        if not r["passed"]:
            failure = ET.SubElement(
                testcase,
                "failure",
                {"message": str(r.get("reason", ""))[:250]},
            )
            failure.text = str(r.get("reason", ""))

    rough_string = ET.tostring(testsuite, encoding="utf-8")
    pretty = minidom.parseString(rough_string).toprettyxml(indent="  ")

    with open(output_xml, "w", encoding="utf-8") as f:
        f.write(pretty)

    print(f"JUnit-style XML report written to: {output_xml}")


def generate_report(
    results: List[Dict[str, Any]],
    output_csv: str = "results.csv",
    output_xml: str = "unit.xml",
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg_score = round(sum(r.get("score", 0.0) for r in results) / total, 2) if total else 0.0

    print("\n" + "=" * 72)
    print("EVAL SUMMARY")
    print("=" * 72)

    by_category = defaultdict(lambda: {"total": 0, "passed": 0, "score_sum": 0.0})
    for r in results:
        cat = by_category[r["category"]]
        cat["total"] += 1
        cat["score_sum"] += r.get("score", 0.0)
        if r["passed"]:
            cat["passed"] += 1

    print(f"{'CATEGORY':30s} {'PASS/TOTAL':>12s} {'AVG SCORE':>12s}")
    print("-" * 72)
    for category, stats in sorted(by_category.items()):
        cat_avg = round(stats["score_sum"] / stats["total"], 2) if stats["total"] else 0.0
        pass_str = f"{stats['passed']}/{stats['total']}"
        print(f"{category:30s} {pass_str:>12s} {cat_avg:>12.2f}")

    print("-" * 72)
    pct = (passed / total * 100) if total else 0.0
    print(f"{'TOTAL':30s} {f'{passed}/{total}':>12s} {avg_score:>12.2f}   ({pct:.1f}% passed)")
    print("=" * 72)

    print("\nPER-TEST-CASE RESULTS:")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{r['id']:12s}] {status:4s}  score={r.get('score', 0.0):>4.1f}/10  ({r['category']})")

    print("\nFAILED CASES (detail):")
    failed_any = False
    for r in results:
        if not r["passed"]:
            failed_any = True
            print(f"  [{r['id']}] ({r['category']}) score={r.get('score', 0.0)}/10 - {r['reason']}")
    if not failed_any:
        print("  None! All test cases passed.")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "category",
                "eval_method",
                "input",
                "response",
                "passed",
                "score",
                "reason",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"\nDetailed CSV report (with per-test-case scores) written to: {output_csv}")

    generate_junit_xml(results, output_xml=output_xml)
    print()