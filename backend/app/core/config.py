import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:80"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/behavioral_integrity_db"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/behavioral_integrity_db"

    # ML Artifacts
    MODEL_PATH: str = "ml/models/xgboost_behavior.json"
    FASTTEXT_MODEL_PATH: str = "ml/models/fasttext_api.bin"
    FAISS_INDEX_PATH: str = "ml/models/faiss_endpoints.index"
    MARKOV_MODEL_PATH: str = "ml/models/markov_transitions.pkl"

    # Security Thresholds
    RISK_THRESHOLD_ALLOW: float = 0.35
    RISK_THRESHOLD_CHALLENGE: float = 0.70

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
