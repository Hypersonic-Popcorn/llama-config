import docker
from typing import cast

from docker.errors import APIError, NotFound
from docker.models.containers import Container

from src.custom_exceptions import ContainerNotRunning
from src.settings import settings


def _get_client() -> docker.DockerClient:
    return docker.DockerClient.from_env()


def get_container() -> Container:
    client = _get_client()
    try:
        name = settings.docker_container_name
        container: Container = client.containers.get(name)  # type: ignore
        return container
    except NotFound:
        msg = f"Container '{settings.docker_container_name}' not found"
        raise ContainerNotRunning(msg)


def container_is_running() -> bool:
    try:
        container = get_container()
        status: str = container.status  # type: ignore[assignment]
        return status == "running"
    except (ContainerNotRunning, APIError):
        return False


def exec_in_container(cmd: str, user: str = "ubuntu") -> tuple[int, str]:
    container = get_container()
    try:
        result = container.exec_run(cmd, user=user)  # type: ignore
        exit_code = result.exit_code
        result_output: bytes = cast(bytes, result.output)
        stdout: str = result_output.decode("utf-8").strip()
        assert exit_code is not None
        return (exit_code, stdout)
    except (NotFound, APIError):
        raise ContainerNotRunning("container exec failed")


def restart_container() -> None:
    container = get_container()
    try:
        container.restart()  # type: ignore[union-attr]
    except (NotFound, APIError) as e:
        raise ContainerNotRunning(str(e))


def get_logs(tail: int = 100) -> list[str]:
    container = get_container()
    try:
        result = container.logs(tail=tail, stderr=True)  # type: ignore
        return result.decode("utf-8").splitlines()
    except (NotFound, APIError):
        raise ContainerNotRunning("logs failed")
