import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

if "GOOGLE_GENAI_USE_VERTEXAI" not in os.environ:
    if os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
    else:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "True":
    if "GOOGLE_CLOUD_PROJECT" not in os.environ:
        import google.auth

        try:
            _, project_id = google.auth.default()
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id or ""
        except Exception:
            pass
    if "GOOGLE_CLOUD_LOCATION" not in os.environ:
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"


@dataclass
class ExpenseAgentConfig:
    model: str = "gemini-3.1-flash-lite"
    review_threshold: float = 100.0


config = ExpenseAgentConfig()
