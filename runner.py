"""
Eval harness runner.

Usage:
    python runner.py
    python runner.py --solution learner_solutions/solution.py --test-cases test_cases/test_cases.json
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from evaluators.rule_based import evaluate_rule_based
from evaluators.llm_judge import evaluate_llm_judge
from report import generate_report

load_dotenv()


def load_solution(solution_path: str):
    """Dynamically import a learner's solution.py and return its get_response function."""
    resolved = Path(solution_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Solution file not found: {resolved}")

    spec = importlib.util.spec_from_file_location("learner_solution", resolved)
    module = importlib.util.module_from_spec(spec)
    sys.modules["learner_solution"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "get_response"):
        raise AttributeError(
            f"{resolved} must define a function `get_response(question: str) -> str`"
        )
    return module.get_response


def load_test_cases(test_cases_path: str):
    with open(test_cases_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("test_cases", [])


def run_tests(get_response, test_cases):
    results = []
    for case in test_cases:
        case_id = case["id"]
        category = case["category"]
        eval_method = case["eval_method"]
        input_text = case["input"]

        print(f"Running [{case_id}] ({category}) ...")

        try:
            actual_response = get_response(input_text)
        except Exception as e:
            results.append(
                {
                    "id": case_id,
                    "category": category,
                    "eval_method": eval_method,
                    "input": input_text,
                    "response": None,
                    "passed": False,
                    "score": 0.0,
                    "reason": f"Solution raised an exception: {e}",
                }
            )
            continue

        if eval_method == "rule_based":
            passed, score, reason = evaluate_rule_based(actual_response, case.get("check", {}))
        elif eval_method == "llm_judge":
            passed, score, reason = evaluate_llm_judge(
                input_text, actual_response, case.get("rubric", "")
            )
        else:
            passed, score, reason = False, 0.0, f"Unknown eval_method: {eval_method}"

        results.append(
            {
                "id": case_id,
                "category": category,
                "eval_method": eval_method,
                "input": input_text,
                "response": actual_response,
                "passed": passed,
                "score": score,
                "reason": reason,
            }
        )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run the ShopEase chatbot eval suite against a learner's solution."
    )
    parser.add_argument(
        "--solution",
        default="learner_solutions/solution.py",
        help="Path to the learner's solution.py file (must define get_response(question: str) -> str)",
    )
    parser.add_argument(
        "--test-cases",
        default="test_cases/test_cases.json",
        help="Path to the test cases JSON file",
    )
    parser.add_argument(
        "--output",
        default="results.csv",
        help="Path to write the CSV report",
    )
    parser.add_argument(
        "--junit-output",
        default="unit.xml",
        help="Path to write the JUnit-style XML report (for platforms that parse test results as JUnit XML)",
    )
    args = parser.parse_args()

    get_response = load_solution(args.solution)
    test_cases = load_test_cases(args.test_cases)

    results = run_tests(get_response, test_cases)
    # generate_report(results, output_csv=args.output)
    generate_report(results, output_csv=args.output, output_xml=args.junit_output)


if __name__ == "__main__":
    main()
