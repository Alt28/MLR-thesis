"""Select a compatible local server without stopping another running process."""
import json
import socket
import urllib.request
from src.config import SCHEMA_VERSION


def server_status(url):
    def read(path):
        with urllib.request.urlopen(url + path, timeout=1) as response:
            return json.load(response)
    try:
        health = read('/api/health')
    except (OSError, ValueError):
        return 'unavailable'
    if not isinstance(health, dict) or health.get('application') != 'transit-lab':
        return 'other'
    try:
        schema = read('/api/schema')
        library = read('/api/datasets/library')
        if schema.get('defaults', {}).get('schema_version') == SCHEMA_VERSION and isinstance(library, list):
            return 'compatible'
    except (OSError, ValueError, AttributeError):
        pass
    return 'outdated'


def port_available(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind((host, port))
        return True
    except OSError:
        return False


def select_server(host, preferred_port):
    if not 1 <= preferred_port <= 65535:
        raise ValueError('The server port must be between 1 and 65535.')
    browser_host = '127.0.0.1' if host == '0.0.0.0' else host
    for port in range(preferred_port, min(preferred_port + 10, 65536)):
        url = f'http://{browser_host}:{port}'
        status = server_status(url)
        if status == 'compatible':
            return port, url, True
        if status == 'unavailable' and port_available(host, port):
            return port, url, False
        if status == 'outdated':
            print(f'The server at {url} needs an update. Checking the next local address...')
    raise ValueError('No compatible or available local address found. Close an older Transit Lab server and reopen the launcher.')
