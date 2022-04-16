from typing import List

from pydantic import BaseSettings


class Settings(BaseSettings):
    github_access_token: str
    google_allowed_domains: List

    class Config:
        env_file = ".env"


settings = Settings()
