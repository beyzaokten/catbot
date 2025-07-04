import os
from typing import Optional

class Settings:
    """Application settings and configuration"""
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    
    # LLM Configuration
    DEFAULT_MODEL: str = "llama3"
    DEFAULT_TEMPERATURE: float = 0.7
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        settings = cls()
        
        settings.API_HOST = os.getenv("API_HOST", settings.API_HOST)
        settings.API_PORT = int(os.getenv("API_PORT", settings.API_PORT))
        settings.DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", settings.DEFAULT_MODEL)
        settings.DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", settings.DEFAULT_TEMPERATURE))
        settings.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)
        settings.DEBUG = os.getenv("DEBUG", "True").lower() == "true"
        settings.ENVIRONMENT = os.getenv("ENVIRONMENT", settings.ENVIRONMENT)
        
        return settings

# Global settings instance
settings = Settings.from_env() 