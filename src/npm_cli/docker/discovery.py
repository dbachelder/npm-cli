"""Docker container discovery logic for NPM.

This module implements three-strategy fallback discovery:
1. By configured container name (fastest, most specific)
2. By Docker Compose service label (flexible for compose deployments)
3. By common name patterns (works with manual deployments)
"""

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container
from rich.console import Console

console = Console()


def get_docker_client() -> docker.DockerClient | None:
    """Get Docker client with graceful error handling.

    Returns:
        Docker client if available, None if Docker daemon not accessible.

    Example:
        >>> client = get_docker_client()
        >>> if client:
        ...     containers = client.containers.list()
    """
    try:
        client = docker.from_env()
        client.ping()  # Verify connection
        return client
    except DockerException as e:
        console.print(f"[yellow]Warning:[/yellow] Docker not available: {e}")
        console.print("Using manual NPM URL configuration instead.")
        return None


def discover_npm_container(
    client: docker.DockerClient,
    container_name: str | None = None,
    service_label: str = "nginx-proxy-manager"
) -> Container | None:
    """Discover NPM container using multiple fallback strategies.

    Strategy 1: By configured container name (if provided)
    Strategy 2: By Docker Compose service label
    Strategy 3: By common name patterns

    Args:
        client: Docker client instance
        container_name: Optional specific container name to search for
        service_label: Docker Compose service name (default: nginx-proxy-manager)

    Returns:
        Container instance if found, None otherwise

    Example:
        >>> client = get_docker_client()
        >>> if client:
        ...     container = discover_npm_container(client)
        ...     if container:
        ...         print(f"Found NPM at {container.name}")
    """
    # Strategy 1: By configured name
    if container_name:
        try:
            return client.containers.get(container_name)
        except NotFound:
            pass  # Fall through to other strategies

    # Strategy 2: By compose service label
    containers = client.containers.list(filters={
        'label': f'com.docker.compose.service={service_label}'
    })
    if containers:
        return containers[0]

    # Strategy 3: By common name patterns
    common_patterns = ['nginx-proxy-manager', 'npm', 'nginxproxymanager']
    for pattern in common_patterns:
        containers = client.containers.list(filters={'name': pattern})
        if containers:
            return containers[0]

    return None
