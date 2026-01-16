"""
Vesla Server API
Main Flask application for handling deployments
"""

import os
import yaml
import logging
import tempfile
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify
import docker

from dns_manager import DNSManager
from builder import ImageBuilder, BuildError
from deployer import ContainerDeployer, DeploymentError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

# Initialize Docker client
docker_client = docker.from_env()

# Initialize managers
dns_manager = DNSManager(config["digitalocean"]["api_token"])
image_builder = ImageBuilder(docker_client)
container_deployer = ContainerDeployer(docker_client, config["docker"]["network"])


# Authentication decorator
def require_auth(f):
    """Require valid API token for endpoint access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning("Missing Authorization header")
            return jsonify({"status": "error", "error": "Missing Authorization header"}), 401

        # Check Bearer token
        if not auth_header.startswith("Bearer "):
            logger.warning("Invalid Authorization format")
            return jsonify({"status": "error", "error": "Invalid Authorization format"}), 401

        token = auth_header[7:]  # Remove "Bearer " prefix

        if token != config["api_token"]:
            logger.warning("Invalid API token")
            return jsonify({"status": "error", "error": "Invalid API token"}), 403

        return f(*args, **kwargs)

    return decorated_function


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "vesla-server"}), 200


@app.route("/api/deploy", methods=["POST"])
@require_auth
def deploy():
    """
    Deploy an application

    Expected multipart/form-data with:
    - code: Tarball file (.tar.gz)
    - config: vesla.yaml content (text)
    """
    try:
        # Validate request
        if "code" not in request.files:
            return jsonify({"status": "error", "error": "Missing 'code' file"}), 400

        if "config" not in request.form:
            return jsonify({"status": "error", "error": "Missing 'config' field"}), 400

        # Parse vesla.yaml
        try:
            vesla_config = yaml.safe_load(request.form["config"])
        except yaml.YAMLError as e:
            return jsonify({"status": "error", "error": f"Invalid vesla.yaml: {str(e)}"}), 400

        # Validate vesla.yaml
        validation_error = validate_vesla_config(vesla_config)
        if validation_error:
            return jsonify({"status": "error", "error": validation_error}), 400

        app_name = vesla_config["app"]
        domain = vesla_config["domain"]

        logger.info(f"Starting deployment for {app_name} at {domain}")

        # Save tarball to temp file
        code_file = request.files["code"]
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tarball_path = tmp.name
            code_file.save(tarball_path)

        try:
            # Step 1: Build Docker image
            logger.info(f"Building Docker image for {app_name}")
            image_id, build_time = image_builder.build_image(
                app_name,
                tarball_path,
                vesla_config,
                max_build_time=config["build"]["max_build_time"]
            )

            # Step 2: Create DNS record
            logger.info(f"Creating DNS record for {domain}")
            subdomain, base_domain = parse_domain(domain)
            server_ip = get_server_ip()

            dns_success = dns_manager.create_a_record(subdomain, base_domain, server_ip)
            if not dns_success:
                logger.warning(f"Failed to create DNS record for {domain}, continuing anyway")

            # Step 3: Deploy container
            logger.info(f"Deploying container for {app_name}")
            container_id = container_deployer.deploy_container(app_name, image_id, vesla_config)

            # Clean up old images
            image_builder.cleanup_old_images(app_name)

            logger.info(f"Successfully deployed {app_name} at https://{domain}")

            return jsonify({
                "status": "success",
                "app": app_name,
                "url": f"https://{domain}",
                "container_id": container_id[:12],
                "build_time": round(build_time, 2),
                "message": "Deployment successful"
            }), 200

        finally:
            # Clean up tarball
            try:
                os.unlink(tarball_path)
            except Exception as e:
                logger.warning(f"Failed to clean up tarball: {e}")

    except BuildError as e:
        logger.error(f"Build error: {str(e)}")
        return jsonify({"status": "error", "error": f"Build failed: {str(e)}"}), 500

    except DeploymentError as e:
        logger.error(f"Deployment error: {str(e)}")
        return jsonify({"status": "error", "error": f"Deployment failed: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500


@app.route("/api/apps/<app_name>", methods=["GET"])
@require_auth
def get_app_status(app_name):
    """Get status of a deployed application"""
    try:
        status = container_deployer.get_container_status(app_name)

        if status:
            return jsonify({"status": "success", "app": app_name, "container": status}), 200
        else:
            return jsonify({"status": "error", "error": "App not found"}), 404

    except Exception as e:
        logger.error(f"Error getting app status: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/apps/<app_name>", methods=["DELETE"])
@require_auth
def delete_app(app_name):
    """Delete a deployed application"""
    try:
        # Remove container
        success = container_deployer.remove_container(app_name)

        if success:
            logger.info(f"Successfully deleted app: {app_name}")
            return jsonify({"status": "success", "message": f"App {app_name} deleted"}), 200
        else:
            return jsonify({"status": "error", "error": "App not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting app: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/apps/<app_name>/logs", methods=["GET"])
@require_auth
def get_app_logs(app_name):
    """Get logs from a deployed application"""
    try:
        tail = request.args.get("tail", default=100, type=int)
        logs = container_deployer.get_container_logs(app_name, tail=tail)

        if logs is not None:
            return jsonify({"status": "success", "app": app_name, "logs": logs}), 200
        else:
            return jsonify({"status": "error", "error": "App not found"}), 404

    except Exception as e:
        logger.error(f"Error getting app logs: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


def validate_vesla_config(vesla_config: dict) -> str:
    """
    Validate vesla.yaml configuration

    Returns:
        Error message if validation fails, None if valid
    """
    # Required fields
    if "app" not in vesla_config:
        return "Missing required field: 'app'"

    if "domain" not in vesla_config:
        return "Missing required field: 'domain'"

    # Validate app name (alphanumeric and hyphens only)
    app_name = vesla_config["app"]
    if not app_name.replace("-", "").replace("_", "").isalnum():
        return "App name must contain only letters, numbers, hyphens, and underscores"

    # Validate domain
    domain = vesla_config["domain"]
    base_domain = domain.split(".", 1)[1] if "." in domain else None

    if not base_domain or base_domain not in config["allowed_domains"]:
        allowed = ", ".join(config["allowed_domains"])
        return f"Domain must use one of the allowed base domains: {allowed}"

    return None


def parse_domain(fqdn: str) -> tuple:
    """
    Parse fully qualified domain name into subdomain and base domain

    Args:
        fqdn: e.g., 'myapp.vesla-app.site'

    Returns:
        Tuple of (subdomain, base_domain)
    """
    parts = fqdn.split(".", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        raise ValueError(f"Invalid domain format: {fqdn}")


def get_server_ip() -> str:
    """Get server's public IP address"""
    import socket
    import urllib.request

    try:
        # Try to get public IP from external service
        with urllib.request.urlopen('https://api.ipify.org', timeout=5) as response:
            return response.read().decode('utf-8')
    except Exception:
        # Fallback to local IP (might not be public)
        return socket.gethostbyname(socket.gethostname())


if __name__ == "__main__":
    logger.info("Starting Vesla Server API")
    logger.info(f"Allowed domains: {config['allowed_domains']}")
    app.run(host="0.0.0.0", port=5001, debug=False)
