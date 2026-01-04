"""Docker container discovery for NPM."""

from npm_cli.docker.discovery import discover_npm_container, get_docker_client

__all__ = ["discover_npm_container", "get_docker_client"]
