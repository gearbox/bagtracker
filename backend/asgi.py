import uvicorn

from backend import application

app = application.create_app()


def run_uvicorn():
    uvicorn.run(
        "asgi:app",
        host=application.settings.bind_host,
        port=application.settings.bind_host_port,
        workers=application.settings.uvicorn_workers,
        reload=True,
    )


if __name__ == "__main__":
    run_uvicorn()
