"""
CodeTrace AI — Application Configuration

All settings are read from environment variables with sensible defaults.
No hardcoded secrets or API keys.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGIN: str = os.getenv("CORS_ORIGIN", "http://localhost:5173")

    # Sandbox execution
    SANDBOX_IMAGE: str = os.getenv("SANDBOX_IMAGE", "codetrace-sandbox:latest")
    EXECUTION_TIMEOUT: int = int(os.getenv("EXECUTION_TIMEOUT", "5"))
    EXECUTION_MEMORY: str = os.getenv("EXECUTION_MEMORY", "128m")
    EXECUTION_CPU: str = os.getenv("EXECUTION_CPU", "0.5")

    # AI Provider
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4o")

    # Limits
    MAX_CODE_SIZE: int = 64 * 1024    # 64 KB
    MAX_INPUT_SIZE: int = 64 * 1024   # 64 KB
    MAX_OUTPUT_SIZE: int = 256 * 1024  # 256 KB

    @property
    def ai_configured(self) -> bool:
        return bool(self.AI_PROVIDER and self.AI_API_KEY)


settings = Settings()
