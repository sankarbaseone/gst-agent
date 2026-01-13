from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GST Reconciliation Agent"
    API_V1_STR: str = "/api"
    
    # Database (Placeholder)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "gst_agent"

    class Config:
        case_sensitive = True

settings = Settings()
