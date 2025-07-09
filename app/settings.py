import os

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[misc]
    BASE: str = Field(default_factory=os.getcwd)
    repl_bin_path: str = ""
    path_to_mathlib: str | None = None
    LOG_LEVEL: str = "INFO"
    MAX_REPLS: int = 2
    MAX_USES: int = 1
    REPL_MEMORY_GB: int = 8
    INIT_REPLS: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")  # type: ignore
    def set_defaults(self) -> "Settings":
        if self.repl_bin_path == "":
            self.repl_bin_path = self.BASE + "/repl/.lake/build/bin/repl"
        if self.path_to_mathlib is None:
            self.path_to_mathlib = self.BASE + "/mathlib4"
        return self


settings = Settings()
