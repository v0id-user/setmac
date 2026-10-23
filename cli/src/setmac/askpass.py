"""One admin password prompt per run, shared by every installer.

Installers run without a terminal, so sudo falls back to the program named in
SUDO_ASKPASS. That program is a tiny shell script that asks this process for
the password over a unix socket in a private temp directory. The password
never lands in a file, an argument or an environment variable.

The first request emits `auth_required` and reads the reply from stdin (the
app's password sheet, or the terminal). The password is checked with
`sudo -S -v` before it is cached for the rest of the run.
"""

from __future__ import annotations

import os
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading

from setmac.output import emit_auth_required, emit_log

MAX_ATTEMPTS = 3

# The socket path is written into the script, not passed in the environment:
# brew runs sudo with a scrubbed environment that keeps SUDO_ASKPASS but drops
# everything else, so a variable would be empty by the time the helper runs.
_HELPER = """#!/bin/sh
exec /usr/bin/nc -U {socket}
"""


class AskpassServer:
    def __init__(self) -> None:
        self._password: str | None = None
        self._cancelled = False
        self._lock = threading.Lock()
        # /tmp keeps the socket path under the 104-byte AF_UNIX limit.
        self._dir = tempfile.mkdtemp(prefix="setmac-askpass-", dir="/tmp")
        os.chmod(self._dir, stat.S_IRWXU)
        self.socket_path = os.path.join(self._dir, "sock")
        self.helper_path = os.path.join(self._dir, "askpass")
        with open(self.helper_path, "w") as f:
            f.write(_HELPER.format(socket=shlex.quote(self.socket_path)))
        os.chmod(self.helper_path, stat.S_IRWXU)

        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.socket_path)
        os.chmod(self.socket_path, stat.S_IRUSR | stat.S_IWUSR)
        self._server.listen(4)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def env(self) -> dict[str, str]:
        return {"SUDO_ASKPASS": self.helper_path}

    def password(self, tool: str | None = None) -> str | None:
        """Return a verified password, prompting the user if needed. None if cancelled."""
        with self._lock:
            if self._password is not None:
                return self._password
            if self._cancelled:
                return None
            message = "Admin password required for installation"
            for _ in range(MAX_ATTEMPTS):
                candidate = _read_password(tool, message)
                if not candidate:
                    self._cancelled = True
                    return None
                if _verify(candidate):
                    self._password = candidate
                    return candidate
                message = "Wrong password. Try again."
            emit_log("Admin password rejected 3 times; skipping admin steps", tool=tool)
            self._cancelled = True
            return None

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            with conn:
                pw = self.password()
                # An empty reply makes sudo fail fast instead of hanging.
                conn.sendall(((pw or "") + "\n").encode())

    def close(self) -> None:
        try:
            self._server.close()
        except OSError:
            pass
        shutil.rmtree(self._dir, ignore_errors=True)
        if self._password is not None:
            subprocess.run(["sudo", "-k"], capture_output=True)


def _read_password(tool: str | None, message: str) -> str:
    emit_auth_required(tool or "setmac", message)
    if sys.stdin.isatty():
        import getpass

        return getpass.getpass("Admin password: ")
    line = sys.stdin.readline()
    return line.rstrip("\n") if line else ""


def _verify(password: str) -> bool:
    result = subprocess.run(
        ["sudo", "-S", "-k", "-v", "-p", ""],
        input=password + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode == 0
