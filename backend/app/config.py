from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    semantic_scholar_api_key: str | None = None
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    request_timeout_seconds: float = 12.0
    database_url: str = "sqlite:///./researchpilot.db"
    genai_provider: str = "none"
    genai_model: str = "gemini-2.5-flash"
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    auth_secret: str = "replace-this-development-secret-before-production"
    otp_development_mode: bool = True
    otp_expiry_minutes: int = 10
    aws_region: str = "ap-south-1"
    bedrock_agent_id: str | None = None
    bedrock_agent_alias_id: str | None = None


settings = Settings()
