# ShopEase Chatbot Eval Harness

An evaluation harness for grading LangChain + Groq customer-support chatbot
implementations against a fixed suite of test cases (normal questions, prompt
injection, out-of-scope handling, system prompt leakage, and more).

## How it works

1. A learner implements `get_response(question: str) -> str` in a Python file
   (see `learner_solutions/solution.py` for a reference implementation).
2. `runner.py` dynamically imports that file and calls `get_response()` once
   per test case in `test_cases/test_cases.json`.
3. Each test case is graded by one of two evaluators:
   - **Rule-based** (`evaluators/rule_based.py`) — deterministic string checks.
     Used for security-flavored categories (prompt injection, system prompt
     leakage, format compliance, edge-case inputs) where you want fast,
     gameable-proof grading.
   - **LLM-as-judge** (`evaluators/llm_judge.py`) — a Groq-hosted model grades
     the response against a natural-language rubric. Used for quality-flavored
     categories (correctness, tone, out-of-scope handling, hallucination).
4. `report.py` prints a pass/fail summary **and a 0-10 score** by category,
   and writes a detailed `results.csv` with a `score` column alongside the
   `passed` verdict for every test case.

## Scoring (0-10 per test case)

Every test case gets both an independent pass/fail verdict **and** a 0-10
score — they aren't derived from each other, so a case can score partial
credit (e.g. 6/10) while still being marked FAIL, or score less than a
perfect 10 while still passing.

- **Rule-based cases**: the score is the proportion of individual sub-checks
  satisfied (e.g. if a case defines 2 checks and only 1 passes, the score is
  5.0/10). A case with no `check` block defined auto-scores 10.0.
- **LLM-judge cases**: the judge model is prompted to return a 0-10 score
  directly, reflecting how well the response satisfies the rubric — not just
  a binary judgment. This allows nuance (e.g. a response that's on the right
  track but incomplete might score 6/10 while still failing the rubric).

The console report shows average score per category and overall; the CSV
has a `score` column per test case for further analysis (e.g. pivoting in
a spreadsheet, tracking a learner's score over multiple submissions).

## Project structure

```
eval_app/
├── learner_solutions/
│   └── solution.py          # reference implementation — replace with a learner's file
├── test_cases/
│   └── test_cases.json      # 45 test cases across 10 scenario categories
├── evaluators/
│   ├── rule_based.py        # deterministic checks
│   └── llm_judge.py         # Groq-based semantic judge
├── runner.py                 # orchestrates loading, running, and reporting
├── report.py                  # formats console summary + CSV
├── config.py                  # central config (reads env vars)
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env and add your real GROQ_API_KEY
```

## Running the eval suite

```bash
python runner.py
```

Optional flags:

```bash
python runner.py \
  --solution path/to/some_learners_solution.py \
  --test-cases test_cases/test_cases.json \
  --output results.csv \
  --junit-output unit.xml
```

This will print a per-category pass/fail summary to the console and write two
report files:
- `results.csv` — every test case's input, response, verdict, score, and reasoning
- `unit.xml` — the same results in JUnit-style XML, for grading platforms
  that expect a JUnit test report rather than a CSV. Each test case is a
  `<testcase>`; a failing case gets a `<failure>` element with the reason,
  and the 0-10 score is attached as a `<property name="score" .../>` under
  each test case (plain JUnit XML has no native score field, so this is the
  standard extension point most JUnit-XML consumers support).

### Config for automated grading platforms

If your grading platform asks for a directory, a test command, an evaluation
command, and a score file (as many CI-style auto-graders do), here's how this
project maps onto that:

| Field | Value |
|---|---|
| Directory | repo root |
| Test Command for user | `python runner.py` |
| Test Command for evaluation | `rm -f unit.xml && python runner.py` |
| Score File(s) for evaluation | `unit.xml` |

The `rm -f unit.xml` before rerunning ensures a stale report from a previous
run is never picked up if the current run fails before writing a new one.

## Test case categories (42 total)

| Category | Count | Eval method | What it checks |
|---|---|---|---|
| normal_question | 5 | llm_judge | Baseline correctness/relevance |
| prompt_injection | 8 | rule_based | Override attempts, fake system messages, DAN/roleplay jailbreaks, base64-encoded instructions, indirect/combo injection |
| out_of_scope | 8 | llm_judge | Unrelated topics, persona hijacking, sensitive-topic redirection, plus boundary cases that test for over-eager refusal |
| system_prompt_leakage | 4 | rule_based | Direct/indirect attempts to extract the system prompt |
| ambiguous_question | 3 | llm_judge | Whether it asks for clarification instead of guessing |
| toxic_adversarial | 3 | rule_based / llm_judge | Handling insults and requests to generate harmful content |
| format_compliance | 2 | rule_based | Numbered lists, word-count limits |
| tone_persona_consistency | 2 | llm_judge | Staying professional/empathetic under pressure |
| hallucination_check | 2 | llm_judge | Not fabricating order data or product specs |
| edge_case_input | 5 | rule_based / llm_judge | Empty input, gibberish, non-English, symbols, minimal input |

## Extending the suite

Add a new entry to `test_cases/test_cases.json`:

```json
{
  "id": "new_01",
  "category": "prompt_injection",
  "eval_method": "rule_based",
  "input": "...",
  "check": {
    "must_not_contain_any": ["..."],
    "should_contain_one_of": ["..."]
  }
}
```

or, for an `llm_judge` case, replace `check` with a `rubric` string describing
what a correct response should do.

## Grading a new learner's submission

Drop their file in anywhere (it just needs a `get_response(question: str) -> str`
function) and point `--solution` at it:

```bash
python runner.py --solution submissions/alice_solution.py --output results_alice.csv
```

## Notes / known limitations

- The LLM-judge currently uses Groq itself (`GROQ_JUDGE_MODEL`, default
  `llama-3.3-70b-versatile`) since no other LLM provider is configured yet.
  Using the same provider for both the solution and the judge carries a mild
  self-grading bias risk — consider swapping in a different provider as judge
  later if grading needs to be more rigorous.
- The interface contract is currently function-based (direct Python import).
  An API-based contract (HTTP endpoint) is a natural next step for testing
  submissions that aren't trusted to run in-process.
- Rule-based checks use simple substring matching, which will need occasional
  tuning as you see real variation in how different solutions phrase refusals.
