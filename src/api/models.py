from typing import Any

from pydantic import BaseModel


class ValidateRequest(BaseModel):
    config: dict[str, Any]
    label: str | None = None


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class ConfigResponse(BaseModel):
    config: dict[str, Any]


class BackupItem(BaseModel):
    backup_id: str
    timestamp: str
    label: str | None


class BackupList(BaseModel):
    backups: list[BackupItem]


class ModelScanResult(BaseModel):
    models: list[dict[str, Any]]
    errors: list[str]


class DockerStatusResponse(BaseModel):
    running: bool


class DockerRestartResponse(BaseModel):
    success: bool
    message: str = ""


class DockerLogsResponse(BaseModel):
    logs: list[str]


class DockerHealthResponse(BaseModel):
    healthy: bool
    message: str


class OptionsResponse(BaseModel):
    llama_server: list[dict[str, Any]]
    llama_swap: list[dict[str, Any]]


class RefreshResponse(BaseModel):
    success: bool
    message: str = ""
