import sys
import os
import socket

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ['PYTHONPATH'] = project_root

import uvicorn


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def pick_available_port(host: str, start_port: int, max_tries: int = 20) -> int:
    for port in range(start_port, start_port + max_tries):
        if is_port_available(host, port):
            return port
    raise RuntimeError(
        f"No free port found in range {start_port}-{start_port + max_tries - 1}"
    )

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    requested_port = int(os.getenv("PORT", "8001"))
    search_limit = int(os.getenv("PORT_SEARCH_LIMIT", "20"))
    port = pick_available_port(host, requested_port, max_tries=search_limit)

    if port != requested_port:
        print(f"Port {requested_port} is busy. Starting on {host}:{port} instead.")

    uvicorn.run("backend.api.main:app", reload=False, host=host, port=port)