from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    docker_container_name: str = "llama-swap"
    config_file: Path = Path("./config.yaml")
    model_dir: Path = Path("./models")
    docs_dir: Path = Path("./llama_docs")
    backup_dir: Path = Path("./config_backups")
    health_check_url: str = "https://llama-swap.tail044fe.ts.net/v1/models"
    health_check_timeout: int = 30
    health_check_interval: int = 2
    log_dir: Path = Path("./logs")


settings = Settings()
