"""
Docker Image Builder for Vesla
Handles runtime detection and Docker image building
"""

import os
import logging
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
import docker
from docker.errors import BuildError as DockerBuildError, APIError

logger = logging.getLogger(__name__)


class BuildError(Exception):
    """Custom exception for build errors"""
    pass


class ImageBuilder:
    """Builds Docker images from application code"""

    def __init__(self, docker_client: docker.DockerClient):
        self.docker = docker_client

    def detect_runtime(self, build_dir: Path) -> str:
        """
        Detect application runtime from project files

        Returns:
            Runtime type: 'dockerfile', 'python', 'node', 'static', or 'unknown'
        """
        # Check for Dockerfile first (user-provided)
        if (build_dir / "Dockerfile").exists():
            logger.info("Found Dockerfile - using custom build")
            return "dockerfile"

        # Check for Python
        if (build_dir / "requirements.txt").exists() or (build_dir / "pyproject.toml").exists():
            logger.info("Detected Python runtime")
            return "python"

        # Check for Node.js
        if (build_dir / "package.json").exists():
            logger.info("Detected Node.js runtime")
            return "node"

        # Check for static site
        if (build_dir / "index.html").exists():
            logger.info("Detected static site")
            return "static"

        logger.warning("Could not detect runtime")
        return "unknown"

    def generate_dockerfile(self, runtime: str, build_dir: Path, config: dict) -> str:
        """
        Generate Dockerfile content based on runtime

        Args:
            runtime: Runtime type (python, node, static)
            build_dir: Build directory path
            config: vesla.yaml configuration

        Returns:
            Dockerfile content as string
        """
        port = config.get("env", {}).get("PORT", "5000")

        if runtime == "python":
            # Detect Python web framework
            entrypoint = self._detect_python_entrypoint(build_dir)

            dockerfile = f"""FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt* pyproject.toml* ./
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir .

# Copy application code
COPY . .

# Expose port
EXPOSE {port}

# Run application
{entrypoint}
"""

        elif runtime == "node":
            # Detect Node.js start command
            start_cmd = self._detect_node_start(build_dir)

            dockerfile = f"""FROM node:20-slim

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production || npm install --production

# Copy application code
COPY . .

# Expose port
EXPOSE {port}

# Run application
{start_cmd}
"""

        elif runtime == "static":
            dockerfile = f"""FROM nginx:alpine

# Copy static files
COPY . /usr/share/nginx/html

# Copy custom nginx config if exists
COPY nginx.conf /etc/nginx/nginx.conf || true

EXPOSE 80
"""

        else:
            raise BuildError(f"Cannot generate Dockerfile for runtime: {runtime}")

        return dockerfile

    def _detect_python_entrypoint(self, build_dir: Path) -> str:
        """Detect Python application entrypoint"""
        # Check for common entry points
        if (build_dir / "app.py").exists():
            return 'CMD ["python", "app.py"]'
        elif (build_dir / "main.py").exists():
            return 'CMD ["python", "main.py"]'
        elif (build_dir / "wsgi.py").exists():
            return 'CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]'
        elif (build_dir / "manage.py").exists():
            # Django app
            return 'CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]'
        else:
            # Default
            return 'CMD ["python", "app.py"]'

    def _detect_node_start(self, build_dir: Path) -> str:
        """Detect Node.js start command"""
        # Try to read package.json for start script
        import json
        try:
            with open(build_dir / "package.json") as f:
                package = json.load(f)
                scripts = package.get("scripts", {})
                if "start" in scripts:
                    return 'CMD ["npm", "start"]'
        except Exception as e:
            logger.warning(f"Could not parse package.json: {e}")

        # Check for common entry points
        if (build_dir / "index.js").exists():
            return 'CMD ["node", "index.js"]'
        elif (build_dir / "server.js").exists():
            return 'CMD ["node", "server.js"]'
        elif (build_dir / "app.js").exists():
            return 'CMD ["node", "app.js"]'
        else:
            return 'CMD ["npm", "start"]'

    def build_image(self, app_name: str, tarball_path: str, vesla_config: dict,
                    max_build_time: int = 600) -> Tuple[str, float]:
        """
        Build Docker image from tarball

        Args:
            app_name: Application name (used for image tag)
            tarball_path: Path to code tarball
            vesla_config: Parsed vesla.yaml configuration
            max_build_time: Maximum build time in seconds

        Returns:
            Tuple of (image_id, build_time_seconds)

        Raises:
            BuildError: If build fails
        """
        import time
        start_time = time.time()

        # Create temporary build directory
        build_dir = Path(tempfile.mkdtemp(prefix=f"vesla-build-{app_name}-"))

        try:
            logger.info(f"Extracting tarball to {build_dir}")
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(build_dir)

            # Detect runtime
            runtime = self.detect_runtime(build_dir)
            if runtime == "unknown":
                raise BuildError("Could not detect application runtime. Please provide a Dockerfile.")

            # Generate Dockerfile if needed
            if runtime != "dockerfile":
                dockerfile_content = self.generate_dockerfile(runtime, build_dir, vesla_config)
                dockerfile_path = build_dir / "Dockerfile"
                dockerfile_path.write_text(dockerfile_content)
                logger.info(f"Generated Dockerfile for {runtime} runtime")

            # Build Docker image
            image_tag = f"{app_name}:latest"
            logger.info(f"Building Docker image: {image_tag}")

            try:
                image, build_logs = self.docker.images.build(
                    path=str(build_dir),
                    tag=image_tag,
                    rm=True,  # Remove intermediate containers
                    timeout=max_build_time
                )

                # Log build output
                for log in build_logs:
                    if 'stream' in log:
                        logger.debug(log['stream'].strip())
                    elif 'error' in log:
                        logger.error(log['error'])

                build_time = time.time() - start_time
                logger.info(f"Successfully built image {image_tag} in {build_time:.2f}s")

                return image.id, build_time

            except DockerBuildError as e:
                raise BuildError(f"Docker build failed: {str(e)}")
            except APIError as e:
                raise BuildError(f"Docker API error: {str(e)}")

        finally:
            # Clean up build directory
            try:
                shutil.rmtree(build_dir)
                logger.debug(f"Cleaned up build directory: {build_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up build directory: {e}")

    def cleanup_old_images(self, app_name: str):
        """Remove old/dangling images for an app"""
        try:
            # Remove dangling images
            self.docker.images.prune(filters={"dangling": True})
            logger.info(f"Cleaned up dangling images for {app_name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old images: {e}")
