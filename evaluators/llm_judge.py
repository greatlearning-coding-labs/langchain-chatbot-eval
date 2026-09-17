"""
LLM-as-judge evaluation.

Used for test cases that need semantic understanding rather than exact string
matching — correctness, tone, out-of-scope handling, hallucination checks,
etc. The judge is a Groq-hosted model, ideally a larger/different model than
whatever the learner's solution uses, to reduce self-grading bias.
"""

import json
import os
from typing import Tuple

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

JUDGE_MODEL = os.environ.get("OpenAI_JUDGE_MODEL", "gpt-5.6-luna")

JUDGE_SYSTEM_PROMPT = """You are a strict, impartial evaluator for a customer support chatbot.
You will be given the user's question, the chatbot's response, and a rubric describing what a
correct/appropriate response should do.

Evaluate the response against the rubric and provide:
1. A verdict: "PASS" if the response adequately satisfies the rubric, "FAIL" otherwise.
2. A score from 0 to 10 measuring how well the response satisfies the rubric, where
   0 = completely fails the rubric, 10 = fully and excellently satisfies the rubric.
   Use the full range - partial credit is expected and encouraged for responses that
   are on the right track but imperfect.
3. A one or two sentence reasoning for your verdict and score.

Respond ONLY with a JSON object in exactly this format, with no other text before or after it:

{"verdict": "PASS" or "FAIL", "score": <integer 0-10>, "reasoning": "<one or two sentence explanation>"}
"""

_judge_llm = None


def _get_judge_llm():
    global _judge_llm
    if _judge_llm is None:
        _judge_llm = ChatOpenAI(
            model=JUDGE_MODEL,
            temperature=0,
            api_key=os.environ.get("OpenAI_Key"),
            base_url=os.environ.get("OpenAI_Base_URL")
        )
    return _judge_llm


def evaluate_llm_judge(question: str, response: str, rubric: str) -> Tuple[bool, float, str]:
    """Returns (passed, score_0_to_10, reasoning)."""
    if response is None:
        return False, 0.0, "No response returned."

    raw_output = ""
    try:
        llm = _get_judge_llm()

        user_content = (
            f"User question:\n{question}\n\n"
            f"Chatbot response:\n{response}\n\n"
            f"Rubric:\n{rubric}"
        )

        messages = [
            SystemMessage(content=JUDGE_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        result = llm.invoke(messages)
        raw_output = result.content.strip()

        # Be tolerant of accidental markdown fences around the JSON output.
        cleaned = raw_output.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(cleaned)
        verdict = str(parsed.get("verdict", "FAIL")).upper()
        reasoning = parsed.get("reasoning", "No reasoning provided.")

        raw_score = parsed.get("score", 0)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(10.0, score))  # clamp to 0-10 in case the judge misbehaves

        return verdict == "PASS", score, reasoning

    except json.JSONDecodeError:
        return False, 0.0, f"Judge did not return valid JSON. Raw output: {raw_output}"
    except Exception as e:
        return False, 0.0, f"Judge call failed: {e}"
