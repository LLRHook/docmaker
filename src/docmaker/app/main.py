"""Main entry point for the Docmaker desktop application."""

import logging
import sys
from pathlib import Path

from pyloid import Pyloid

from docmaker.app.ipc import DocmakerAPI

logger = logging.getLogger(__name__)

# Get the frontend directory path
FRONTEND_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
DEV_URL = "http://localhost:5173"


def create_app(dev_mode: bool = False) -> Pyloid:
    """Create and configure the Pyloid application.

    Args:
        dev_mode: If True, load from dev server instead of built files

    Returns:
        Configured Pyloid application instance
    """
    app = Pyloid(
        app_name="Docmaker",
        single_instance=True,
    )

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if dev_mode else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    return app


def create_window(app: Pyloid, dev_mode: bool = False, project_path: str | None = None):
    """Create the main application window.

    Args:
        app: Pyloid application instance
        dev_mode: If True, load from dev server
        project_path: Optional path to load on startup
    """
    # Create the API instance
    api = DocmakerAPI()

    window = app.create_window(
        title="Docmaker - Code Knowledge Graph",
        width=1400,
        height=900,
        IPCs=[api],
    )

    # Set window properties
    window.set_minimum_size(800, 600)

    # Load the frontend
    if dev_mode:
        logger.info(f"Loading development server at {DEV_URL}")
        window.load_url(DEV_URL)
        window.open_dev_tools()
    else:
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            logger.info(f"Loading frontend from {index_path}")
            window.load_file(str(index_path))
        else:
            logger.error(f"Frontend not found at {index_path}")
            logger.info("Run 'npm run build' in the frontend directory first")
            # Load a simple error page
            window.load_url(
                "data:text/html,<html><body style='font-family:system-ui;padding:40px;'>"
                "<h1>Frontend Not Built</h1>"
                "<p>Please build the frontend first:</p>"
                "<pre>cd frontend && npm install && npm run build</pre>"
                "</body></html>"
            )

    window.show()
    window.focus()

    # If a project path was provided, signal the frontend to load it
    if project_path:
        # We'll pass this via a custom event after the window loads
        window.emit("load-project", {"path": project_path})

    return window


def run_app(dev_mode: bool = False, project_path: str | None = None) -> int:
    """Run the Docmaker desktop application.

    Args:
        dev_mode: If True, connect to Vite dev server
        project_path: Optional project path to load on startup

    Returns:
        Exit code
    """
    try:
        app = create_app(dev_mode)
        create_window(app, dev_mode, project_path)
        app.run()
        return 0
    except Exception:
        logger.exception("Application error")
        return 1


if __name__ == "__main__":
    # When run directly, start in dev mode
    sys.exit(run_app(dev_mode=True))
