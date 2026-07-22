"""
CodeTrace AI — Application Configuration

All settings are read from environment variables with sensible defaults.
No hardcoded secrets or API keys.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Server ──────────────────────────────────────────────────────────
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # ── CORS ────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # Example: "http://localhost:5173,https://codetrace-ai.pages.dev"
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into a list."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    # ── Execution Mode ──────────────────────────────────────────────────
    # "subprocess" — Subprocess runner (all environments, recommended)
    # "docker"     — Docker sandbox (local dev only, requires Docker daemon)
    EXECUTION_MODE: str = os.getenv("EXECUTION_MODE", "subprocess")

    # Docker sandbox settings (used when EXECUTION_MODE=docker)
    SANDBOX_IMAGE: str = os.getenv("SANDBOX_IMAGE", "codetrace-sandbox:latest")
    EXECUTION_TIMEOUT: int = int(os.getenv("EXECUTION_TIMEOUT", "5"))
    EXECUTION_MEMORY: str = os.getenv("EXECUTION_MEMORY", "128m")
    EXECUTION_CPU: str = os.getenv("EXECUTION_CPU", "0.5")

    # ── AI Provider ─────────────────────────────────────────────────────
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4o")

    @property
    def ai_configured(self) -> bool:
        return bool(self.AI_PROVIDER and self.AI_API_KEY)

    # ── Limits ──────────────────────────────────────────────────────────
    MAX_CODE_SIZE: int = int(os.getenv("MAX_CODE_SIZE", str(64 * 1024)))
    MAX_INPUT_SIZE: int = int(os.getenv("MAX_INPUT_SIZE", str(64 * 1024)))
    MAX_OUTPUT_SIZE: int = int(os.getenv("MAX_OUTPUT_SIZE", str(256 * 1024)))


settings = Settings()
