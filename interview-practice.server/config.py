import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:"
        f"{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES

    OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL")
    OPENROUTER_API_KEY_FILE = os.environ.get("OPENROUTER_API_KEY_FILE")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "60"))
    PORTRAIT_GENERATION_ENABLED = os.environ.get(
        "PORTRAIT_GENERATION_ENABLED", "true"
    ).strip().lower() not in ("0", "false", "no", "off")
