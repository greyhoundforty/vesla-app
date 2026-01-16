"""
Vesla Dashboard - Mission Control
Displays deployed applications and their status
"""

from flask import Flask, render_template, jsonify, request, Response
import subprocess
import json
import logging
from datetime import datetime
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def docker_cli(args):
    """Execute docker command and return output or parsed JSON"""
    try:
        result = subprocess.run(
            ['docker'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            # First, try to parse as regular JSON (works for inspect, stats)
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # If that fails, return raw output (for line-delimited JSON from ps)
                return result.stdout
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker CLI error: {e.stderr}")
        raise


def get_container_info(container_dict):
    """Extract relevant info from a container dict"""
    try:
        # Get container labels and parse from string to dict
        labels_str = container_dict.get('Labels', '')
        labels = {}
        if labels_str:
            for label in labels_str.split(','):
                if '=' in label:
                    key, value = label.split('=', 1)
                    labels[key] = value

        # Extract container name first for filtering
        name = container_dict.get('Names', 'unknown').lstrip('/')

        # Filter out system containers
        if name in ['traefik', 'vesla-api']:
            return None

        # Check if this is a Vesla-deployed app (has Traefik labels)
        if labels.get('traefik.enable') != 'true':
            return None
        status = container_dict.get('State', 'unknown')

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

        # Get container details for stats
        container_id = container_dict.get('ID', '')
        inspect_data = docker_cli(['inspect', container_id])[0]

        # Get container stats
        stats = docker_cli(['stats', '--no-stream', '--format', '{{json .}}', container_id])

        # Calculate uptime
        started_at = inspect_data['State']['StartedAt']
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

        # Get image info - prefer RepoTags over long ID
        image = 'unknown'
        if 'Config' in inspect_data and 'Image' in inspect_data['Config']:
            # Get short image ID from Config.Image (sha256:xxx...)
            image_id = inspect_data['Config']['Image']
            if image_id.startswith('sha256:'):
                image = image_id[7:19]  # Use first 12 chars of sha256

        # Try to get a better name from RepoTags if available
        if 'RepoTags' in inspect_data['Config'] and inspect_data['Config']['RepoTags']:
            repo_tags = inspect_data['Config']['RepoTags']
            if repo_tags and repo_tags[0] != '<none>:<none>':
                image = repo_tags[0]

        # Parse memory from stats
        mem_usage_str = stats.get('MemUsage', '0B / 0B')
        try:
            mem_parts = mem_usage_str.split(' / ')
            mem_usage_mb = parse_memory(mem_parts[0])
            mem_limit_mb = parse_memory(mem_parts[1])
            mem_percent = (mem_usage_mb / mem_limit_mb * 100) if mem_limit_mb > 0 else 0
        except:
            mem_usage_mb = 0
            mem_percent = 0

        return {
            'name': name,
            'status': status,
            'domain': domain,
            'port': port,
            'uptime': uptime,
            'image': image,
            'mem_usage_mb': round(mem_usage_mb, 1),
            'mem_percent': round(mem_percent, 1),
            'started_at': started_at,
        }
    except Exception as e:
        logger.error(f"Error getting container info for {container_dict.get('Names', 'unknown')}: {e}")
        return None


def parse_memory(mem_str):
    """Parse memory string like '100MiB' to MB"""
    mem_str = mem_str.strip()
    if 'GiB' in mem_str or 'GB' in mem_str:
        return float(mem_str.replace('GiB', '').replace('GB', '').strip()) * 1024
    elif 'MiB' in mem_str or 'MB' in mem_str:
        return float(mem_str.replace('MiB', '').replace('MB', '').strip())
    elif 'KiB' in mem_str or 'KB' in mem_str:
        return float(mem_str.replace('KiB', '').replace('KB', '').strip()) / 1024
    elif 'B' in mem_str:
        return float(mem_str.replace('B', '').strip()) / 1024 / 1024
    return 0


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/deployments')
def get_deployments():
    """Get all deployed applications"""
    try:
        # Get list of containers
        containers = docker_cli(['ps', '--format', '{{json .}}', '--no-trunc'])

        # Parse line-delimited JSON
        container_list = []
        if containers:
            for line in containers.strip().split('\n'):
                if line.strip():
                    container_list.append(json.loads(line))

        deployments = []
        for container in container_list:
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


@app.route('/traefik')
@app.route('/traefik/')
def traefik_dashboard_redirect():
    """Redirect /traefik to /traefik/dashboard/"""
    from flask import redirect
    return redirect('/traefik/dashboard/', code=302)


@app.route('/traefik/<path:path>')
def traefik_proxy(path):
    """Proxy requests to Traefik API"""
    # Forward to Traefik API on port 8080
    url = f'http://127.0.0.1:8080/{path}'

    # Forward the request
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )

        # Build response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        response = Response(resp.content, resp.status_code, headers)
        return response
    except Exception as e:
        logger.error(f"Error proxying to Traefik: {e}")
        return jsonify({'error': 'Failed to connect to Traefik'}), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
