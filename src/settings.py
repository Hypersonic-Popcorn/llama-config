from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    docker_container_name: str = "llama-swap"
    config_path: Path = Path("/home/aria/docker/llama-swap/config/config.yaml")
    model_directory: Path = Path("/home/aria/ai/models/llm/GGUF")
    docs_dir: Path = Path("/home/aria/projects/python/llama-config/llama_docs")
    backup_dir: Path = Path("/home/aria/projects/python/llama-config/config_backups")
    health_check_url: str = "https://llama-swap.tail044fe.ts.net/v1/models"
    health_check_timeout: int = 30
    health_check_interval: int = 2
    log_file: Path = Path("/home/aria/projects/python/llama-config/logs")


settings = Settings()
