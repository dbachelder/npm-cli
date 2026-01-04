"""Tests for Docker container discovery."""

import pytest
from docker.errors import DockerException
from unittest.mock import MagicMock, Mock

from npm_cli.docker.discovery import discover_npm_container, get_docker_client


class TestGetDockerClient:
    """Tests for get_docker_client helper."""

    def test_get_docker_client_success(self, mocker):
        """Should return Docker client when Docker is available."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_env = mocker.patch("npm_cli.docker.discovery.docker.from_env")
        mock_from_env.return_value = mock_client

        result = get_docker_client()

        assert result is mock_client
        mock_client.ping.assert_called_once()

    def test_get_docker_client_docker_not_available(self, mocker):
        """Should return None when Docker is not running."""
        mock_from_env = mocker.patch("npm_cli.docker.discovery.docker.from_env")
        mock_from_env.side_effect = DockerException("Docker daemon not available")

        result = get_docker_client()

        assert result is None


class TestDiscoverNpmContainer:
    """Tests for discover_npm_container function."""

    def test_discover_by_configured_name(self, mocker):
        """Should find container by configured name (Strategy 1)."""
        mock_container = Mock()
        mock_container.name = "my-custom-npm"

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container

        result = discover_npm_container(mock_client, container_name="my-custom-npm")

        assert result is mock_container
        mock_client.containers.get.assert_called_once_with("my-custom-npm")

    def test_discover_by_compose_label(self, mocker):
        """Should find container by compose service label (Strategy 2)."""
        mock_container = Mock()
        mock_container.name = "project_npm_1"

        mock_client = MagicMock()
        # Strategy 1 fails (no configured name)
        # Strategy 2 succeeds (compose label)
        mock_client.containers.list.return_value = [mock_container]

        result = discover_npm_container(mock_client)

        assert result is mock_container
        # Should be called with compose label filter
        mock_client.containers.list.assert_called_once_with(
            filters={"label": "com.docker.compose.service=nginx-proxy-manager"}
        )

    def test_discover_by_common_name_pattern(self, mocker):
        """Should find container by common name patterns (Strategy 3)."""
        mock_container = Mock()
        mock_container.name = "nginx-proxy-manager"

        mock_client = MagicMock()
        # Strategy 1 fails (no configured name)
        # Strategy 2 fails (no compose label)
        # Strategy 3 succeeds (common name pattern)
        mock_client.containers.list.side_effect = [
            [],  # No containers with compose label
            [mock_container],  # Found with 'nginx-proxy-manager' name
        ]

        result = discover_npm_container(mock_client)

        assert result is mock_container
        # Should try compose label first, then common patterns
        assert mock_client.containers.list.call_count == 2

    def test_discover_returns_none_when_not_found(self, mocker):
        """Should return None if no container found after all strategies."""
        mock_client = MagicMock()
        # All strategies fail
        mock_client.containers.list.return_value = []

        result = discover_npm_container(mock_client)

        assert result is None

    def test_discover_handles_configured_name_not_found(self, mocker):
        """Should fallback to other strategies when configured name not found."""
        from docker.errors import NotFound

        mock_container = Mock()
        mock_container.name = "npm"

        mock_client = MagicMock()
        # Strategy 1 fails (NotFound)
        mock_client.containers.get.side_effect = NotFound("Container not found")
        # Strategy 2 fails (no compose label)
        # Strategy 3 succeeds with 'npm' pattern
        mock_client.containers.list.side_effect = [
            [],  # No containers with compose label
            [],  # No containers with 'nginx-proxy-manager'
            [mock_container],  # Found with 'npm' pattern
        ]

        result = discover_npm_container(mock_client, container_name="nonexistent")

        assert result is mock_container

    def test_discover_extracts_network_settings(self, mocker):
        """Should extract container network settings and ports."""
        mock_container = Mock()
        mock_container.name = "nginx-proxy-manager"
        mock_container.attrs = {
            "NetworkSettings": {
                "Networks": {
                    "bridge": {
                        "IPAddress": "172.17.0.2"
                    }
                },
                "Ports": {
                    "81/tcp": [{"HostIp": "0.0.0.0", "HostPort": "81"}]
                }
            }
        }

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]

        result = discover_npm_container(mock_client)

        assert result is mock_container
        # Verify we can access network info from container
        assert result.attrs["NetworkSettings"]["Networks"]["bridge"]["IPAddress"] == "172.17.0.2"
        assert result.attrs["NetworkSettings"]["Ports"]["81/tcp"][0]["HostPort"] == "81"
