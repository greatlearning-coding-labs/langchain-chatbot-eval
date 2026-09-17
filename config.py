"""
Central configuration for the eval harness.

All values are read from environment variables (see .env.example).
Import from this module if you want a single place to reference config,
though evaluators/solution.py also read os.environ directly for simplicity.
"""

import os

OPENAI_API_KEY = os.environ.get("OpenAI_Key")
LEARNER_MODEL = os.environ.get("OPENAI_LEARNER_MODEL", "gpt-5.6-luna")
JUDGE_MODEL = os.environ.get("OPENAI_JUDGE_MODEL", "gpt-5.6-luna")

