from unittest.mock import MagicMock, patch

import pytest
from docker.errors import NotFound

from src.core.docker_manager import (
    container_is_running,
    exec_in_container,
    get_container,
    get_logs,
    restart_container,
)

mock_patch = "src.core.docker_manager.docker.DockerClient.from_env"


def test_get_container_returns_container():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.get.return_value = MagicMock()

        result = get_container()

        assert result == mock_client.containers.get.return_value
        mock_client.containers.get.assert_called_once_with("llama-swap")


def test_get_container_raises_if_not_found():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.get.side_effect = NotFound("not found")

        from src.custom_exceptions import ContainerNotRunning

        with pytest.raises(ContainerNotRunning):
            get_container()


def test_ensure_container_running_returns_container_when_running():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container

        from src.core.docker_manager import _ensure_container_running

        result = _ensure_container_running()
        assert result == mock_container


def test_ensure_container_running_raises_when_paused():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "paused"
        mock_client.containers.get.return_value = mock_container

        from src.custom_exceptions import ContainerNotRunning
        from src.core.docker_manager import _ensure_container_running

        with pytest.raises(ContainerNotRunning):
            _ensure_container_running()


def test_container_is_running_returns_true():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container

        result = container_is_running()
        assert result is True


def test_container_is_running_returns_false_when_not_found():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.get.side_effect = NotFound("not found")

        result = container_is_running()
        assert result is False


def test_container_is_running_returns_false_when_paused():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "paused"
        mock_client.containers.get.return_value = mock_container

        result = container_is_running()
        assert result is False


def test_container_is_running_returns_false_when_created():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "created"
        mock_client.containers.get.return_value = mock_container

        result = container_is_running()
        assert result is False


def test_exec_in_container_returns_exit_code_and_stdout():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container

        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.output = b"hello world"
        mock_container.exec_run.return_value = mock_result

        exit_code, stdout = exec_in_container("echo hello")

        assert exit_code == 0
        assert stdout == "hello world"
        mock_container.exec_run.assert_called_once_with(  # noqa: E501
            "echo hello", user="ubuntu"
        )


def test_exec_in_container_uses_custom_user():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container

        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.output = b"output"
        mock_container.exec_run.return_value = mock_result

        exec_in_container("echo hello", user="root")

        mock_container.exec_run.assert_called_once_with(  # noqa: E501
            "echo hello", user="root"
        )


def test_exec_in_container_raises_on_exec_error():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_container.exec_run.side_effect = NotFound("not found")

        from src.custom_exceptions import ContainerNotRunning

        with pytest.raises(ContainerNotRunning):
            exec_in_container("echo hello")


def test_exec_in_container_raises_when_not_running():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container

        from src.custom_exceptions import ContainerNotRunning

        with pytest.raises(ContainerNotRunning):
            exec_in_container("echo hello")


def test_restart_container_calls_restart():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container

        restart_container()

        mock_container.restart.assert_called_once()


def test_restart_container_raises_on_error():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_container.restart.side_effect = NotFound("not found")

        from src.custom_exceptions import ContainerNotRunning

        with pytest.raises(ContainerNotRunning):
            restart_container()


def test_restart_container_raises_when_not_running():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container

        from src.custom_exceptions import ContainerNotRunning

        with pytest.raises(ContainerNotRunning):
            restart_container()


def test_get_logs_returns_list_of_lines():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_container.logs.return_value = b"line1\nline2\nline3"

        logs = get_logs()

        assert logs == ["line1", "line2", "line3"]


def test_get_logs_uses_custom_tail():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_container.logs.return_value = b"log"

        get_logs(tail=50)

        mock_container.logs.assert_called_once_with(tail=50, stderr=True)


def test_get_logs_raises_on_error():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_container.logs.side_effect = NotFound("not found")

        from src.custom_exceptions import ContainerNotRunning

        with pytest.raises(ContainerNotRunning):
            get_logs()


def test_get_logs_raises_when_not_running():
    with patch(mock_patch) as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_container = MagicMock()
        mock_container.status = "created"
        mock_client.containers.get.return_value = mock_container

        from src.custom_exceptions import ContainerNotRunning

        with pytest.raises(ContainerNotRunning):
            get_logs()
