from backend.app.config import get_settings
from backend.daemon.ipc.server import serve
from backend.daemon.startup import run_startup_tasks


def main() -> None:
    run_startup_tasks()
    settings = get_settings()
    serve(settings.daemon_socket_path)


if __name__ == "__main__":
    main()
