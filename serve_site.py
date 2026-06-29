#!/usr/bin/env python3
from __future__ import annotations

import functools
import select
import subprocess
import sys
import termios
import threading
import tty
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from build_site import ROOT, load_config

REBUILD_KEY = "\x12"  # Ctrl+R


class SiteServer(ThreadingHTTPServer):
    allow_reuse_address = True


def rebuild_site(lock: threading.Lock) -> None:
    if not lock.acquire(blocking=False):
        print("\nRebuild already running.", flush=True)
        return

    try:
        print("\nRebuilding site with `just quick`...", flush=True)
        result = subprocess.run(["just", "quick"], cwd=ROOT)
        if result.returncode == 0:
            print("Rebuild complete. Press Ctrl+R to rebuild again, Ctrl+C to stop.", flush=True)
        else:
            print(
                f"Rebuild failed with exit code {result.returncode}.",
                flush=True,
            )
    finally:
        lock.release()


def hotkey_loop(stop_event: threading.Event, rebuild_lock: threading.Lock) -> None:
    while not stop_event.is_set():
        readable, _, _ = select.select([sys.stdin], [], [], 0.25)
        if not readable:
            continue

        char = sys.stdin.read(1)
        if char == REBUILD_KEY:
            rebuild_site(rebuild_lock)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    config = load_config()
    handler = functools.partial(
        SimpleHTTPRequestHandler,
        directory=str(config.public_dir),
    )
    server = SiteServer(("", port), handler)

    stop_event = threading.Event()
    rebuild_lock = threading.Lock()
    old_terminal = None

    if sys.stdin.isatty():
        fd = sys.stdin.fileno()
        old_terminal = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        threading.Thread(
            target=hotkey_loop,
            args=(stop_event, rebuild_lock),
            daemon=True,
        ).start()

    print(
        f"Serving {config.public_dir} at http://127.0.0.1:{port}/",
        flush=True,
    )
    if old_terminal is not None:
        print("Press Ctrl+R to rebuild, Ctrl+C to stop.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.", flush=True)
    finally:
        stop_event.set()
        server.server_close()
        if old_terminal is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_terminal)


if __name__ == "__main__":
    main()
