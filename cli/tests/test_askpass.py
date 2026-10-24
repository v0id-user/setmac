import subprocess
import sys

import pytest

from setmac import askpass


@pytest.mark.skipif(sys.platform != "darwin", reason="the askpass helper uses macOS nc -U")
def test_askpass_helper_returns_verified_password(monkeypatch):
    prompts = []
    monkeypatch.setattr(askpass, "_read_password", lambda tool, msg: prompts.append(msg) or ["bad", "good"][len(prompts) - 1])
    monkeypatch.setattr(askpass, "_verify", lambda pw: pw == "good")
    server = askpass.AskpassServer()
    try:
        env = server.env()
        for _ in range(2):
            # An empty environment, like the one brew gives sudo.
            out = subprocess.run([env["SUDO_ASKPASS"], "Password:"], env={},
                                 capture_output=True, text=True, timeout=10)
            assert out.stdout == "good\n"
        assert prompts == ["Admin password required for installation", "Wrong password. Try again."]
    finally:
        server.close()
