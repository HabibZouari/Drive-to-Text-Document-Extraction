"""Application settings, read from environment variables (and a local .env file)."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    max_file_mb: int

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        max_file_mb=int(os.getenv("MAX_FILE_MB", "25")),
    )
