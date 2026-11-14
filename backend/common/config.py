import os


def env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


DATABASE_URL = env(
    "DATABASE_URL", "postgresql+psycopg://firesafe:firesafe@localhost:5432/firesafe"
)

# NASA Physical Sciences Informatics (PSI) public web-service base URL.
PSI_API_BASE = env("PSI_API_BASE", "https://psi.nasa.gov/geode-py/ws")
PSI_SITE_BASE = env("PSI_SITE_BASE", "https://psi.nasa.gov/physci/repo")

# Optional: enables Claude-powered summaries and Q&A in the insights service.
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-opus-5-5")
