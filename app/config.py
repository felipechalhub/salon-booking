from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    app_env: str = "development"
    secret_key: str
    admin_username: str
    admin_password_hash: str
    resend_api_key: str = ""
    resend_from: str = "onboarding@resend.dev"

    class Config:
        env_file = ".env"

settings = Settings()