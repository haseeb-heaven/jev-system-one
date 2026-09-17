import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    jev_api_key: str
    jev_model: str
    llm_api_key: str
    llm_model: str
    log_level: str

    @classmethod
    def from_env(cls, require_keys: bool = True) -> "Settings":
        load_dotenv()
        jev_key = os.getenv("JEV_API_KEY", "").strip()
        llm_key = os.getenv("LLM_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        if require_keys and not jev_key:
            raise ConfigError("JEV_API_KEY is missing. Add it to .env.")
        if require_keys and not llm_key:
            raise ConfigError("OPENAI_API_KEY or LLM_API_KEY is missing. Add it to .env.")
        return cls(
            jev_api_key=jev_key,
            jev_model=os.getenv("JEV_MODEL", "jev-latest"),
            llm_api_key=llm_key,
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
