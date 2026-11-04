import os

from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


BIFROST_URL = env("BIFROST_URL", "http://localhost:8080").rstrip("/")
EXTRACTOR_MODEL = env("EXTRACTOR_MODEL", "groq/openai/gpt-oss-20b")
JUDGE_MODEL = env("JUDGE_MODEL", "groq/openai/gpt-oss-120b")
BUDGET = float(env("BUDGET_USD_PER_RUN", "0.10"))
HALF_LIFE = {"HIGH": 30, "MEDIUM": 180, "LOW": 730}
WEIGHTS = {"verdict": 0.35, "authority": 0.2, "recency": 0.3, "agreement": 0.15}
