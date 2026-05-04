import logging

import httpx
from fastapi import APIRouter

from src.core.docker_manager import (
    container_is_running,
    restart_container,
    get_logs,
    get_container_stdout_logs,
    get_container,
    exec_in_container,
)
from src.settings import settings
from src.custom_exceptions import ContainerNotRunning

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
def docker_status():
    if container_is_running():
        return "RUNNING"
    return "STOPPED"


@router.post("/start")
def docker_start():
    try:
        container = get_container()
        container.start()  # type: ignore
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/stop")
def docker_stop():
    try:
        container = get_container()
        container.stop()  # type: ignore
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/restart", response_model=dict)
def docker_restart():
    try:
        restart_container()
        return {"success": True}
    except ContainerNotRunning as e:
        return {"success": False, "message": str(e)}


@router.get("/logs", response_model=dict)
def docker_logs(tail: int = 100):
    try:
        logs = get_logs(tail=tail)
        return {"logs": logs}
    except ContainerNotRunning:
        return {"logs": ["Container not running"]}


@router.get("/llama-swap-logs")
def llama_swap_logs(tail: int = 100):
    try:
        logs = get_container_stdout_logs(tail=tail)
        return {"logs": logs}
    except ContainerNotRunning:
        return {"logs": ["Container not running"]}


@router.get("/health", response_model=dict)
def docker_health():
    try:
        with httpx.Client(verify=False) as client:
            resp = client.get(settings.health_check_url, timeout=10)
            if resp.status_code == 200:
                return {"healthy": True, "message": "llama-swap is healthy"}
            return {"healthy": False, "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"healthy": False, "message": str(e)}
