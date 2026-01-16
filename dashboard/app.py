"""
Vesla Dashboard - Mission Control
Displays deployed applications and their status
"""

from flask import Flask, render_template, jsonify
import docker
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Docker client lazily
docker_client = None


def get_docker_client():
    """Get Docker client, initializing if needed"""
    global docker_client
    if docker_client is None:
        try:
            docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
    return docker_client


def get_container_info(container):
    """Extract relevant info from a container"""
    try:
        # Get container labels
        labels = container.labels

        # Check if this is a Vesla-deployed app (has Traefik labels)
        if not labels.get('traefik.enable') == 'true':
            return None

        # Extract info
        name = container.name
        status = container.status

        # Get domain from Traefik router rule
        domain = None
        for key, value in labels.items():
            if 'traefik.http.routers' in key and '.rule' in key:
                # Extract domain from Host(`domain.com`) format
                if 'Host(' in value:
                    domain = value.split('Host(`')[1].split('`')[0]
                    break

        # Get port from service label
        port = None
        for key, value in labels.items():
            if 'traefik.http.services' in key and '.loadbalancer.server.port' in key:
                port = value
                break

        # Get container stats
        stats = container.stats(stream=False)

        # Calculate uptime
        started_at = container.attrs['State']['StartedAt']
        started_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        uptime_seconds = (datetime.now(started_time.tzinfo) - started_time).total_seconds()

        # Format uptime
        if uptime_seconds < 60:
            uptime = f"{int(uptime_seconds)}s"
        elif uptime_seconds < 3600:
            uptime = f"{int(uptime_seconds / 60)}m"
        elif uptime_seconds < 86400:
            uptime = f"{int(uptime_seconds / 3600)}h {int((uptime_seconds % 3600) / 60)}m"
        else:
            uptime = f"{int(uptime_seconds / 86400)}d {int((uptime_seconds % 86400) / 3600)}h"

        # Get image info
        image_tag = container.image.tags[0] if container.image.tags else container.image.short_id

        # Memory usage
        mem_stats = stats.get('memory_stats', {})
        mem_usage = mem_stats.get('usage', 0)
        mem_limit = mem_stats.get('limit', 0)
        mem_percent = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0

        return {
            'name': name,
            'status': status,
            'domain': domain,
            'port': port,
            'uptime': uptime,
            'image': image_tag,
            'mem_usage_mb': round(mem_usage / 1024 / 1024, 1),
            'mem_percent': round(mem_percent, 1),
            'started_at': started_at,
        }
    except Exception as e:
        logger.error(f"Error getting container info: {e}")
        return None


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/deployments')
def get_deployments():
    """Get all deployed applications"""
    try:
        client = get_docker_client()
        containers = client.containers.list(all=False)

        deployments = []
        for container in containers:
            info = get_container_info(container)
            if info:
                deployments.append(info)

        # Sort by name
        deployments.sort(key=lambda x: x['name'])

        return jsonify({
            'status': 'operational',
            'timestamp': datetime.utcnow().isoformat(),
            'deployments': deployments,
            'total': len(deployments)
        })
    except Exception as e:
        logger.error(f"Error fetching deployments: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'service': 'vesla-dashboard',
        'status': 'healthy'
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
