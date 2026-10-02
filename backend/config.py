import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from root directory
env_path = Path(__file__).resolve().parent.parent / ".env"

def reload_env():
    """Dynamically re-read .env to detect added/updated API keys immediately."""
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)

# Initial load
reload_env()

class Settings:
    @property
    def LLM_PROVIDER(self) -> str:
        reload_env()
        return os.getenv("LLM_PROVIDER", "gemini").lower()
    
    @property
    def GEMINI_API_KEY(self) -> str:
        reload_env()
        return os.getenv("GEMINI_API_KEY", "")
    
    @property
    def GEMINI_MODEL(self) -> str:
        reload_env()
        return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    
    @property
    def GROQ_API_KEY(self) -> str:
        reload_env()
        return os.getenv("GROQ_API_KEY", "")
    
    @property
    def GROQ_MODEL(self) -> str:
        reload_env()
        return os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    @property
    def OPENAI_API_KEY(self) -> str:
        reload_env()
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def ANTHROPIC_API_KEY(self) -> str:
        reload_env()
        return os.getenv("ANTHROPIC_API_KEY", "")
    
    @property
    def OLLAMA_BASE_URL(self) -> str:
        reload_env()
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        
    @property
    def OLLAMA_MODEL(self) -> str:
        reload_env()
        return os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")

    @property
    def ADMIN_API_KEY(self) -> str:
        reload_env()
        return os.getenv("ADMIN_API_KEY", "")
    
    # Weather APIs
    OPEN_METEO_FORECAST_URL: str = os.getenv(
        "OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast"
    )
    OPEN_METEO_GEOCODING_URL: str = os.getenv(
        "OPEN_METEO_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search"
    )
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    SOPS_DIR: Path = Path(os.getenv("SOPS_DIR", str(BASE_DIR / "sops"))).resolve()
    
    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

settings = Settings()
