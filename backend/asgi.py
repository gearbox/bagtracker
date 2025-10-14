import sys
from pathlib import Path

import uvicorn

from backend import application

app = application.create_app()


def run_uvicorn():
    """
    Run Uvicorn with configuration from uvicorn_config.py
    This function is used for local development
    """
    from pprint import pprint

    # Try to load production config
    try:
        # Add project root to path if running from backend/
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from uvicorn_config import config

        # Override reload for development
        config["reload"] = True
        config["reload_dirs"] = ["backend"]
        config["workers"] = 1  # Reload only works with 1 worker
        config["log_level"] = "debug"
        print("🔄 Running in DEVELOPMENT mode with auto-reload.\nUsing config:")
        pprint(config)
        uvicorn.run(**config)
    except ImportError as e:
        # Fallback to basic config if uvicorn_config.py not found
        config = {
            "app": "backend.asgi:app",
            "host": application.settings.bind_host,
            "port": application.settings.bind_host_port,
            "workers": application.settings.uvicorn_workers,
            "reload": True,
        }
        print(f"❌ Error importing modules: {e}\nFallback to the basic config:")
        pprint(config)
        uvicorn.run(**config)


def run_production():
    """
    Run Uvicorn in production mode with full configuration
    """
    # Add project root to path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from uvicorn_config import config

    print(f"🚀 Running in PRODUCTION mode with {config['workers']} workers")
    uvicorn.run(**config)


if __name__ == "__main__":
    run_uvicorn()
