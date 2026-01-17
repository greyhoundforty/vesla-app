from flask import Flask, render_template, jsonify, request
import docker
from datetime import datetime
import json
import logging
import os

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

# Connect to Docker daemon
try:
    docker_client = docker.from_env()
    app.logger.info("Connected to Docker daemon")
except Exception as e:
    app.logger.error(f"Failed to connect to Docker: {e}")
    docker_client = None


def is_vesla_app(container):
    """Check if container is a Vesla-managed app"""
    # Look for vesla labels or naming convention
    labels = container.labels or {}
    name = container.name or ""
    
    return (
        labels.get("vesla.app") == "true" or
        labels.get("vesla") == "true" or
        "vesla-" in name.lower()
    )


def format_container_info(container):
    """Format container info for JSON response"""
    try:
        state = container.attrs.get("State", {})
        config = container.attrs.get("Config", {})
        
        return {
            "id": container.id[:12],
            "name": container.name,
            "status": container.status,
            "image": config.get("Image", "unknown"),
            "created": container.attrs.get("Created", ""),
            "started": state.get("StartedAt", ""),
            "ports": container.ports or {},
            "labels": container.labels or {},
            "is_running": container.status == "running",
        }
    except Exception as e:
        app.logger.error(f"Error formatting container {container.name}: {e}")
        return None


@app.route("/")
def index():
    """Console home page"""
    return render_template("console.html")


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "vesla-console",
        "docker_connected": docker_client is not None
    })


@app.route("/api/apps")
def get_apps():
    """Get all Vesla-managed applications"""
    if not docker_client:
        return jsonify({"error": "Docker not connected"}), 500
    
    try:
        containers = docker_client.containers.list(all=True)
        
        # Filter to Vesla apps
        vesla_apps = []
        for container in containers:
            if is_vesla_app(container):
                info = format_container_info(container)
                if info:
                    vesla_apps.append(info)
        
        # Also get system containers (traefik, portainer, etc)
        system_containers = []
        system_names = ["traefik", "portainer", "vesla-api", "vesla-dashboard"]
        for container in containers:
            if any(name in container.name.lower() for name in system_names):
                info = format_container_info(container)
                if info:
                    system_containers.append(info)
        
        return jsonify({
            "apps": vesla_apps,
            "system": system_containers,
            "total": len(containers)
        })
    except Exception as e:
        app.logger.error(f"Error fetching apps: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/apps/<container_name>/logs")
def get_app_logs(container_name):
    """Get logs for a specific container"""
    if not docker_client:
        return jsonify({"error": "Docker not connected"}), 500
    
    try:
        # Get tail parameter from query string (default 100 lines)
        tail = request.args.get("tail", 100, type=int)
        
        container = docker_client.containers.get(container_name)
        
        # Get logs with timestamps
        logs = container.logs(
            tail=tail,
            timestamps=True,
            stream=False
        ).decode("utf-8")
        
        return jsonify({
            "container": container_name,
            "logs": logs,
            "lines": len(logs.split("\n"))
        })
    except docker.errors.NotFound:
        return jsonify({"error": f"Container '{container_name}' not found"}), 404
    except Exception as e:
        app.logger.error(f"Error fetching logs for {container_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/apps/<container_name>/stats")
def get_app_stats(container_name):
    """Get resource stats for a container"""
    if not docker_client:
        return jsonify({"error": "Docker not connected"}), 500
    
    try:
        container = docker_client.containers.get(container_name)
        
        if container.status != "running":
            return jsonify({
                "container": container_name,
                "status": container.status,
                "stats": None
            })
        
        # Get stats (one-shot, not streaming)
        stats = container.stats(stream=False)
        
        # Extract key metrics
        cpu_stats = stats.get("cpu_stats", {})
        memory_stats = stats.get("memory_stats", {})
        
        # Calculate CPU percentage
        cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - \
                   stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 0) - \
                      stats.get("precpu_stats", {}).get("system_cpu_usage", 0)
        cpu_percent = (cpu_delta / system_delta * 100.0) if system_delta > 0 else 0
        
        return jsonify({
            "container": container_name,
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage": memory_stats.get("usage", 0),
            "memory_limit": memory_stats.get("limit", 0),
            "memory_percent": round(
                (memory_stats.get("usage", 0) / memory_stats.get("limit", 1)) * 100,
                2
            ) if memory_stats.get("limit", 0) > 0 else 0,
            "pids": stats.get("pids_stats", {}).get("current", 0)
        })
    except docker.errors.NotFound:
        return jsonify({"error": f"Container '{container_name}' not found"}), 404
    except Exception as e:
        app.logger.error(f"Error fetching stats for {container_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/apps/<container_name>/action", methods=["POST"])
def container_action(container_name):
    """Perform an action on a container (restart, stop, etc.)"""
    if not docker_client:
        return jsonify({"error": "Docker not connected"}), 500
    
    try:
        action = request.json.get("action")
        container = docker_client.containers.get(container_name)
        
        if action == "restart":
            container.restart()
            return jsonify({"status": "success", "message": f"Restarted {container_name}"})
        
        elif action == "stop":
            container.stop()
            return jsonify({"status": "success", "message": f"Stopped {container_name}"})
        
        elif action == "start":
            container.start()
            return jsonify({"status": "success", "message": f"Started {container_name}"})
        
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400
    
    except docker.errors.NotFound:
        return jsonify({"error": f"Container '{container_name}' not found"}), 404
    except Exception as e:
        app.logger.error(f"Error performing action on {container_name}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
