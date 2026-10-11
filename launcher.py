"""Launcher GroupPay Desktop — démarre Django + ouvre une fenêtre native."""
import os
import socket
import sys
import threading
import time
import urllib.request

# Forcer le mode desktop AVANT d'importer Django
os.environ.setdefault("GROUPPAY_MODE", "desktop")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_server(port):
    from django.core.management import execute_from_command_line
    sys.argv = ["manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"]
    execute_from_command_line(sys.argv)


def _wait(port, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    port = _free_port()
    threading.Thread(target=_run_server, args=(port,), daemon=True).start()

    if not _wait(port):
        print("Erreur : le serveur Django ne démarre pas.")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"
    try:
        import webview
        webview.create_window("GroupPay", url, width=1280, height=820)
        webview.start()
    except ImportError:
        import webbrowser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
