import asyncio
import logging

import httpx
from fastapi import APIRouter

from src.api.models import (
    BackupList,
    BackupItem,
    ConfigResponse,
    RefreshResponse,
    ValidateRequest,
    ValidateResponse,
)
from src.core.docker_manager import restart_container, get_container
from src.core.yaml_handler import (
    read_config,
    write_config,
    list_backups,
    restore_backup,
)
from src.core.validator import validate_config
from src.custom_exceptions import ContainerNotRunning
from src.settings import settings

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("", response_model=ConfigResponse)
def get_config():
    config = read_config()
    return ConfigResponse(config=config)


@router.post("", response_model=ValidateResponse)
async def save_config(request: ValidateRequest):
    result = validate_config(request.config)
    if not result.valid:
        return ValidateResponse(
            valid=False,
            errors=result.errors,
            warnings=result.warnings,
        )

    write_config(request.config, label=request.label)

    try:
        restart_container()
    except ContainerNotRunning:
        return ValidateResponse(
            valid=True,
            errors=[],
            warnings=["Container restart failed"],
        )

    try:
        await _wait_for_health()
    except Exception as e:
        logger.error("Health check failed after config save: %s", e)
        _rollback()
        return ValidateResponse(
            valid=False,
            errors=["Container failed to start after config change"],
            warnings=[str(e)],
        )

    return ValidateResponse(valid=True, errors=[], warnings=[])


@router.get("/backups", response_model=BackupList)
def get_backups():
    backup_list = list_backups()
    items = [
        BackupItem(
            backup_id=b.get("backup_id", ""),
            timestamp=b.get("timestamp", ""),
            label=b.get("label"),
        )
        for b in backup_list
    ]
    return BackupList(backups=items)


@router.post("/restore/{backup_id}")
def restore(backup_id: str):
    try:
        restore_backup(backup_id)
        restart_container()
    except ContainerNotRunning as e:
        return {"error": str(e)}

    return {"success": True}


async def _wait_for_health():
    timeout = settings.health_check_timeout
    interval = settings.health_check_interval

    try:
        async with httpx.AsyncClient(verify=False) as client:
            for _ in range(timeout // interval):
                try:
                    resp = await client.get(settings.health_check_url, timeout=5)
                    if resp.status_code == 200:
                        return
                except (
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                    httpx.TimeoutException,
                ):
                    pass
                await asyncio.sleep(interval)

        raise Exception("Health check timeout")
    except httpx.RequestError:
        raise Exception("Health check request failed")


def _rollback():
    try:
        backup_list = list_backups()
        if backup_list:
            last_backup = backup_list[-1]
            restore_backup(last_backup.get("backup_id", ""))
            restart_container()
    except Exception:
        pass
