from __future__ import annotations

import logging
import threading
import webbrowser

from ui.main_window import create_app_server, set_webview_window
from utils.config import APP_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("desmos_clone")


def launch_window(url: str, server_thread: threading.Thread) -> None:
    try:
        import webview

        win = webview.create_window(
            title=APP_CONFIG.window_title,
            url=url,
            width=APP_CONFIG.window_width,
            height=APP_CONFIG.window_height,
            min_size=(APP_CONFIG.window_min_width, APP_CONFIG.window_min_height),
            background_color=APP_CONFIG.dark_background,
        )
        set_webview_window(win)
        webview.start()
    except ImportError:
        logger.info("pywebview nicht installiert – öffne im Browser: %s", url)
        webbrowser.open(url)
        try:
            server_thread.join()
        except KeyboardInterrupt:
            logger.info("Beende Anwendung…")


def main() -> None:
    server = create_app_server(host=APP_CONFIG.host, port=APP_CONFIG.port)
    port = server.server_address[1]
    url = f"http://{APP_CONFIG.host}:{port}/"

    server_thread = threading.Thread(
        target=server.serve_forever,
        name="GraphingAppServer",
        daemon=True,
    )
    server_thread.start()
    logger.info("App läuft auf %s (Strg+C zum Beenden)", url)

    try:
        launch_window(url, server_thread)
    finally:
        set_webview_window(None)
        server.shutdown()
        server.server_close()
        logger.info("App sauber beendet.")


if __name__ == "__main__":
    main()
