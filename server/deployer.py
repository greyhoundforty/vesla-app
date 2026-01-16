"""
Container Deployer for Vesla
Handles Docker container deployment with Traefik integration
"""

import logging
import docker
from docker.errors import APIError, NotFound
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Custom exception for deployment errors"""
    pass


class ContainerDeployer:
    """Deploys and manages Docker containers with Traefik labels"""

    def __init__(self, docker_client: docker.DockerClient, network_name: str):
        self.docker = docker_client
        self.network_name = network_name

    def deploy_container(self, app_name: str, image_id: str, vesla_config: dict) -> str:
        """
        Deploy a container with Traefik labels

        Args:
            app_name: Application name (used for container name)
            image_id: Docker image ID to deploy
            vesla_config: Parsed vesla.yaml configuration

        Returns:
            Container ID

        Raises:
            DeploymentError: If deployment fails
        """
        domain = vesla_config.get("domain")
        if not domain:
            raise DeploymentError("No domain specified in vesla.yaml")

        # Stop and remove existing container if exists
        self._stop_existing_container(app_name)

        # Prepare environment variables
        env_vars = self._prepare_environment(vesla_config)

        # Prepare resource limits
        resources = self._prepare_resources(vesla_config)

        # Prepare Traefik labels
        labels = self._prepare_traefik_labels(app_name, domain, vesla_config)

        # Get port from config
        port = vesla_config.get("env", {}).get("PORT", "5000")

        try:
            logger.info(f"Deploying container for {app_name}")

            container = self.docker.containers.run(
                image=image_id,
                name=app_name,
                detach=True,
                network=self.network_name,
                environment=env_vars,
                labels=labels,
                restart_policy={"Name": "unless-stopped"},
                **resources
            )

            logger.info(f"Successfully deployed container {container.id[:12]} for {app_name}")
            logger.info(f"App accessible at: https://{domain}")

            return container.id

        except APIError as e:
            raise DeploymentError(f"Failed to deploy container: {str(e)}")

    def _stop_existing_container(self, app_name: str):
        """Stop and remove existing container if it exists"""
        try:
            container = self.docker.containers.get(app_name)
            logger.info(f"Stopping existing container: {app_name}")
            container.stop(timeout=10)
            container.remove()
            logger.info(f"Removed existing container: {app_name}")
        except NotFound:
            logger.debug(f"No existing container found for {app_name}")
        except Exception as e:
            logger.warning(f"Error stopping existing container: {e}")

    def _prepare_environment(self, vesla_config: dict) -> Dict[str, str]:
        """Prepare environment variables for container"""
        env_vars = vesla_config.get("env", {})

        # Ensure PORT is set
        if "PORT" not in env_vars:
            env_vars["PORT"] = "5000"

        return env_vars

    def _prepare_resources(self, vesla_config: dict) -> dict:
        """Prepare resource limits for container"""
        resources_config = vesla_config.get("resources", {})

        resources = {}

        # Memory limit
        if "memory" in resources_config:
            resources["mem_limit"] = resources_config["memory"]
        else:
            resources["mem_limit"] = "512m"  # Default

        # CPU limit
        if "cpus" in resources_config:
            cpus = float(resources_config["cpus"])
            resources["nano_cpus"] = int(cpus * 1e9)
        else:
            resources["nano_cpus"] = int(0.5 * 1e9)  # Default 0.5 CPUs

        return resources

    def _prepare_traefik_labels(self, app_name: str, domain: str, vesla_config: dict) -> dict:
        """
        Prepare Traefik labels for container

        Args:
            app_name: Application name
            domain: Domain for routing
            vesla_config: Vesla configuration

        Returns:
            Dictionary of Docker labels for Traefik
        """
        port = vesla_config.get("env", {}).get("PORT", "5000")

        labels = {
            # Enable Traefik
            "traefik.enable": "true",

            # HTTP Router
            f"traefik.http.routers.{app_name}.rule": f"Host(`{domain}`)",
            f"traefik.http.routers.{app_name}.entrypoints": "websecure",
            f"traefik.http.routers.{app_name}.tls": "true",
            f"traefik.http.routers.{app_name}.tls.certresolver": "digitalocean",

            # Service (backend)
            f"traefik.http.services.{app_name}.loadbalancer.server.port": str(port),

            # Metadata
            "vesla.managed": "true",
            "vesla.app": app_name,
            "vesla.domain": domain,
        }

        # Add health check if specified
        if "health_check" in vesla_config:
            health_path = vesla_config["health_check"]
            labels[f"traefik.http.services.{app_name}.loadbalancer.healthcheck.path"] = health_path
            labels[f"traefik.http.services.{app_name}.loadbalancer.healthcheck.interval"] = "30s"

        return labels

    def get_container_status(self, app_name: str) -> Optional[dict]:
        """
        Get status of a deployed container

        Args:
            app_name: Application name

        Returns:
            Dictionary with container status or None if not found
        """
        try:
            container = self.docker.containers.get(app_name)
            container.reload()  # Refresh status

            return {
                "id": container.id[:12],
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                "created": container.attrs["Created"],
                "ports": container.attrs["NetworkSettings"]["Ports"],
            }
        except NotFound:
            return None
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return None

    def stop_container(self, app_name: str) -> bool:
        """
        Stop a running container

        Args:
            app_name: Application name

        Returns:
            True if successful, False otherwise
        """
        try:
            container = self.docker.containers.get(app_name)
            logger.info(f"Stopping container: {app_name}")
            container.stop(timeout=10)
            return True
        except NotFound:
            logger.warning(f"Container not found: {app_name}")
            return False
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False

    def remove_container(self, app_name: str) -> bool:
        """
        Remove a container

        Args:
            app_name: Application name

        Returns:
            True if successful, False otherwise
        """
        try:
            container = self.docker.containers.get(app_name)
            logger.info(f"Removing container: {app_name}")

            # Stop if running
            if container.status == "running":
                container.stop(timeout=10)

            container.remove()
            return True
        except NotFound:
            logger.warning(f"Container not found: {app_name}")
            return False
        except Exception as e:
            logger.error(f"Error removing container: {e}")
            return False

    def get_container_logs(self, app_name: str, tail: int = 100) -> Optional[str]:
        """
        Get container logs

        Args:
            app_name: Application name
            tail: Number of lines to return

        Returns:
            Log output as string or None if container not found
        """
        try:
            container = self.docker.containers.get(app_name)
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode("utf-8")
        except NotFound:
            logger.warning(f"Container not found: {app_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting container logs: {e}")
            return None

    def list_all_apps(self) -> list:
        """
        List all Vesla-managed containers

        Returns:
            List of dictionaries with app information
        """
        try:
            # Get all containers with vesla.managed label
            containers = self.docker.containers.list(
                all=True,
                filters={"label": "vesla.managed=true"}
            )

            apps = []
            for container in containers:
                labels = container.labels
                apps.append({
                    "name": labels.get("vesla.app", container.name),
                    "domain": labels.get("vesla.domain", "N/A"),
                    "status": container.status,
                    "id": container.id[:12],
                    "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                    "created": container.attrs["Created"]
                })

            return apps

        except Exception as e:
            logger.error(f"Error listing apps: {e}")
            return []
