"""Integration smoke test with disposable databases and local Nuxt/FastAPI servers.

Run: .venv/Scripts/python.exe scripts/test_frontend.py (frontend deps must be installed).
AI provider calls are covered separately by catalog_service tests.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT.parent / "frontend"
SECRET = "integration-test-only-secret-1234567890"


def main():
    sys.stdout.reconfigure(errors="replace")
    processes = []
    logs = []
    with tempfile.TemporaryDirectory(prefix="ai-sana-integration-") as directory:
        env = {**os.environ, "ENV": "development", "JWT_SECRET_KEY": SECRET,
               "PYTHONPATH": str(ROOT), "AUTH_SERVICE_URL": "http://127.0.0.1:18001",
               "CATALOG_SERVICE_URL": "http://127.0.0.1:18004", "RATE_LIMIT_PER_MINUTE": "1000",
               "NUXT_GATEWAY_URL": "http://127.0.0.1:18000", "NUXT_PUBLIC_API_BASE": "/api/gateway",
               "AUTH_TEST_FRONTEND": "http://127.0.0.1:13000",
               "AUTH_TEST_GATEWAY": "http://127.0.0.1:18000/api/v1",
               "AUTH_TEST_JWT_SECRET": SECRET, "NUXT_TELEMETRY_DISABLED": "1"}
        node = shutil.which("node")
        if not node:
            raise RuntimeError("Node.js is required")

        def launch(name, command, cwd, extra=None):
            log = open(Path(directory) / f"{name}.log", "w+", encoding="utf-8")
            logs.append((name, log))
            processes.append(subprocess.Popen(command, cwd=cwd, env={**env, **(extra or {})},
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                start_new_session=os.name != "nt"))

        def wait(url):
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError("A test server exited")
                try:
                    with urllib.request.urlopen(url, timeout=3):
                        return
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.5)
            raise RuntimeError(f"Server did not become ready: {url}")

        try:
            for name, port in [("auth_service", 18001), ("catalog_service", 18004), ("api_gateway", 18000)]:
                launch(name, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       ROOT / name, {"DATABASE_URL": f"sqlite+aiosqlite:///{Path(directory, name + '.db').as_posix()}"})
            wait("http://127.0.0.1:18001/health")
            wait("http://127.0.0.1:18004/health")
            wait("http://127.0.0.1:18000/healthz")
            launch("nuxt", [node, "node_modules/nuxt/bin/nuxt.mjs", "dev", "--host", "127.0.0.1", "--port", "13000"], FRONTEND)
            wait("http://127.0.0.1:13000/api/gateway/healthz")
            for test in ["auth.integration.mjs", "catalog.integration.mjs"]:
                subprocess.run([node, f"tests/{test}"], cwd=FRONTEND, env=env, check=True, timeout=180)
        except Exception:
            for name, log in logs:
                log.flush()
                print(f"--- {name} ---", flush=True)
                print(Path(log.name).read_text(encoding="utf-8", errors="replace")[-5000:], flush=True)
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        import signal
                        os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=15)
            for _, log in logs:
                log.close()


if __name__ == "__main__":
    main()
