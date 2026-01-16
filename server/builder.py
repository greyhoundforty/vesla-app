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
            Runtime type: 'dockerfile', 'python', 'node', 'go', 'ruby', 'php',
            'java', 'rust', 'dotnet', 'static', or 'unknown'
        """
        # Check for Dockerfile first (user-provided)
        if (build_dir / "Dockerfile").exists():
            logger.info("Found Dockerfile - using custom build")
            return "dockerfile"

        # Check for Go
        if (build_dir / "go.mod").exists() or (build_dir / "main.go").exists():
            logger.info("Detected Go runtime")
            return "go"

        # Check for Rust
        if (build_dir / "Cargo.toml").exists():
            logger.info("Detected Rust runtime")
            return "rust"

        # Check for Python
        if (build_dir / "requirements.txt").exists() or \
           (build_dir / "pyproject.toml").exists() or \
           (build_dir / "Pipfile").exists() or \
           (build_dir / "setup.py").exists():
            logger.info("Detected Python runtime")
            return "python"

        # Check for Node.js
        if (build_dir / "package.json").exists():
            logger.info("Detected Node.js runtime")
            return "node"

        # Check for Ruby
        if (build_dir / "Gemfile").exists() or \
           (build_dir / "config.ru").exists():
            logger.info("Detected Ruby runtime")
            return "ruby"

        # Check for PHP
        if (build_dir / "composer.json").exists() or \
           (build_dir / "index.php").exists():
            logger.info("Detected PHP runtime")
            return "php"

        # Check for Java/Maven
        if (build_dir / "pom.xml").exists():
            logger.info("Detected Java (Maven) runtime")
            return "java-maven"

        # Check for Java/Gradle
        if (build_dir / "build.gradle").exists() or \
           (build_dir / "build.gradle.kts").exists():
            logger.info("Detected Java (Gradle) runtime")
            return "java-gradle"

        # Check for .NET
        if any(build_dir.glob("*.csproj")) or \
           any(build_dir.glob("*.fsproj")) or \
           any(build_dir.glob("*.vbproj")):
            logger.info("Detected .NET runtime")
            return "dotnet"

        # Check for static site (should be last)
        if (build_dir / "index.html").exists():
            logger.info("Detected static site")
            return "static"

        logger.warning("Could not detect runtime")
        return "unknown"

    def generate_dockerfile(self, runtime: str, build_dir: Path, config: dict) -> str:
        """
        Generate secure Dockerfile content based on runtime

        Args:
            runtime: Runtime type (python, node, go, ruby, php, java, rust, dotnet, static)
            build_dir: Build directory path
            config: vesla.yaml configuration

        Returns:
            Dockerfile content as string
        """
        port = config.get("env", {}).get("PORT", "5000")

        if runtime == "python":
            entrypoint = self._detect_python_entrypoint(build_dir)
            dockerfile = f"""FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt* pyproject.toml* Pipfile* setup.py* ./
RUN pip install --no-cache-dir -U pip && \\
    (pip install --no-cache-dir -r requirements.txt || \\
     pip install --no-cache-dir . || \\
     ([ -f Pipfile ] && pip install pipenv && pipenv install --system --deploy))

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE {port}

{entrypoint}
"""

        elif runtime == "node":
            start_cmd = self._detect_node_start(build_dir)
            dockerfile = f"""FROM node:20-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production || npm install --production

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE {port}

{start_cmd}
"""

        elif runtime == "go":
            dockerfile = f"""# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum* ./
RUN go mod download

# Copy source code
COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o app .

# Runtime stage
FROM alpine:3.19

# Install ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates

# Create non-root user
RUN adduser -D -u 1000 appuser

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/app .

# Change ownership
RUN chown appuser:appuser /app/app

USER appuser

EXPOSE {port}

CMD ["./app"]
"""

        elif runtime == "rust":
            dockerfile = f"""# Build stage
FROM rust:1.75-slim AS builder

WORKDIR /app

# Copy manifests
COPY Cargo.toml Cargo.lock* ./

# Copy source code
COPY . .

# Build release binary
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \\
    ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/* ./

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE {port}

CMD ["./app"]
"""

        elif runtime == "ruby":
            entrypoint = self._detect_ruby_entrypoint(build_dir)
            dockerfile = f"""FROM ruby:3.2-slim

# Install dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy Gemfile
COPY Gemfile Gemfile.lock* ./
RUN bundle install --deployment --without development test

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE {port}

{entrypoint}
"""

        elif runtime == "php":
            dockerfile = f"""FROM php:8.2-fpm-alpine

# Install dependencies
RUN apk add --no-cache nginx supervisor

# Create non-root user
RUN adduser -D -u 1000 appuser

WORKDIR /app

# Copy composer files if exist
COPY composer.json composer.lock* ./
RUN if [ -f composer.json ]; then \\
        php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');" && \\
        php composer-setup.php --install-dir=/usr/local/bin --filename=composer && \\
        composer install --no-dev --optimize-autoloader; \\
    fi

# Copy application code
COPY . .

# Configure PHP-FPM to run as appuser
RUN sed -i 's/user = www-data/user = appuser/g' /usr/local/etc/php-fpm.d/www.conf && \\
    sed -i 's/group = www-data/group = appuser/g' /usr/local/etc/php-fpm.d/www.conf

# Change ownership
RUN chown -R appuser:appuser /app

EXPOSE {port}

CMD ["php-fpm"]
"""

        elif runtime == "java-maven":
            dockerfile = f"""# Build stage
FROM maven:3.9-eclipse-temurin-21-alpine AS builder

WORKDIR /app

# Copy pom.xml
COPY pom.xml .
RUN mvn dependency:go-offline

# Copy source and build
COPY src ./src
RUN mvn package -DskipTests

# Runtime stage
FROM eclipse-temurin:21-jre-alpine

# Create non-root user
RUN adduser -D -u 1000 appuser

WORKDIR /app

# Copy jar from builder
COPY --from=builder /app/target/*.jar app.jar

# Change ownership
RUN chown appuser:appuser /app/app.jar

USER appuser

EXPOSE {port}

CMD ["java", "-jar", "app.jar"]
"""

        elif runtime == "java-gradle":
            dockerfile = f"""# Build stage
FROM gradle:8.5-jdk21-alpine AS builder

WORKDIR /app

# Copy gradle files
COPY build.gradle* settings.gradle* gradlew* gradle/ ./

# Copy source and build
COPY . .
RUN gradle build --no-daemon -x test

# Runtime stage
FROM eclipse-temurin:21-jre-alpine

# Create non-root user
RUN adduser -D -u 1000 appuser

WORKDIR /app

# Copy jar from builder
COPY --from=builder /app/build/libs/*.jar app.jar

# Change ownership
RUN chown appuser:appuser /app/app.jar

USER appuser

EXPOSE {port}

CMD ["java", "-jar", "app.jar"]
"""

        elif runtime == "dotnet":
            dockerfile = f"""# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS builder

WORKDIR /app

# Copy project files
COPY *.csproj* *.fsproj* *.vbproj* ./
RUN dotnet restore || true

# Copy source and build
COPY . .
RUN dotnet publish -c Release -o out

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine

# Create non-root user
RUN adduser -D -u 1000 appuser

WORKDIR /app

# Copy built app
COPY --from=builder /app/out .

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE {port}

ENV ASPNETCORE_URLS=http://+:{port}

ENTRYPOINT ["dotnet", "app.dll"]
"""

        elif runtime == "static":
            dockerfile = f"""FROM nginx:1.25-alpine

# Copy static files
COPY . /usr/share/nginx/html

# Copy custom nginx config if exists
COPY nginx.conf /etc/nginx/nginx.conf 2>/dev/null || true

# Create non-root user (nginx alpine already has nginx user)
RUN chown -R nginx:nginx /usr/share/nginx/html

# Run as non-root
USER nginx

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

    def _detect_ruby_entrypoint(self, build_dir: Path) -> str:
        """Detect Ruby application entrypoint"""
        # Check for Rack config (Rails, Sinatra, etc.)
        if (build_dir / "config.ru").exists():
            return 'CMD ["bundle", "exec", "rackup", "-o", "0.0.0.0"]'
        # Check for Rails
        elif (build_dir / "config" / "environment.rb").exists():
            return 'CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]'
        # Check for Sinatra
        elif (build_dir / "app.rb").exists():
            return 'CMD ["bundle", "exec", "ruby", "app.rb", "-o", "0.0.0.0"]'
        else:
            return 'CMD ["bundle", "exec", "ruby", "app.rb"]'

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
