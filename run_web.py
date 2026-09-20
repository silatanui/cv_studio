"""
Launcher script for Algorithmic CV Optimizer Web Application.
"""

import sys
import uvicorn


def start_server(host: str = "127.0.0.1", port: int = 8000):
    print("=" * 60)
    print("STARTING ALGORITHMIC CV OPTIMIZER WEB APPLICATION")
    print("=" * 60)
    print(f"Local Web UI: http://{host}:{port}")
    print("Press Ctrl+C to stop the server.")
    print("=" * 60)

    uvicorn.run("app:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    start_server()
