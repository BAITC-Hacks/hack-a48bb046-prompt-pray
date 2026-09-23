"""Integration smoke test with disposable databases and local Nuxt/FastAPI servers.

Run: .venv/Scripts/python.exe scripts/test_frontend.py (frontend deps must be installed).
Add --browser for Playwright against a production build and local AI fixture.
"""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from threading import Thread
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT.parent / "frontend"
SECRET = "integration-test-only-secret-1234567890"


def main():
    browser = "--browser" in sys.argv
    sys.stdout.reconfigure(errors="replace")
    processes = []
    logs = []
    ai = None
    if browser:
        from browser_ai_fixture import create_server
        ai = create_server()
        Thread(target=ai.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix="ai-sana-integration-") as directory:
        sockets = [socket.socket() for _ in range(4)]
        try:
            for listener in sockets:
                listener.bind(("127.0.0.1", 0))
            auth_port, catalog_port, gateway_port, frontend_port = [s.getsockname()[1] for s in sockets]
        finally:
            for listener in sockets:
                listener.close()
        env = {**os.environ, "ENV": "development", "JWT_SECRET_KEY": SECRET,
               "PYTHONPATH": str(ROOT), "AUTH_SERVICE_URL": f"http://127.0.0.1:{auth_port}",
               "CATALOG_SERVICE_URL": f"http://127.0.0.1:{catalog_port}", "RATE_LIMIT_PER_MINUTE": "1000",
               "NUXT_GATEWAY_URL": f"http://127.0.0.1:{gateway_port}", "NUXT_PUBLIC_API_BASE": "/api/gateway",
               "NUXT_BUILD_DIR": str(FRONTEND / "node_modules/.cache/nuxt" / Path(directory).name),
               "AUTH_TEST_FRONTEND": f"http://127.0.0.1:{frontend_port}",
               "AUTH_TEST_GATEWAY": f"http://127.0.0.1:{gateway_port}/api/v1",
               "AUTH_TEST_JWT_SECRET": SECRET, "NUXT_TELEMETRY_DISABLED": "1"}
        if ai:
            env["AI_SERVICE_URL"] = f"http://127.0.0.1:{ai.server_port}"
            env["BROWSER_TEST_BASE_URL"] = env["AUTH_TEST_FRONTEND"]
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
            for name, port in [("auth_service", auth_port), ("catalog_service", catalog_port), ("api_gateway", gateway_port)]:
                launch(name, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-proxy-headers"],
                       ROOT / name, {"DATABASE_URL": f"sqlite+aiosqlite:///{Path(directory, name + '.db').as_posix()}"})
            wait(f"http://127.0.0.1:{auth_port}/health")
            wait(f"http://127.0.0.1:{catalog_port}/health")
            wait(f"http://127.0.0.1:{gateway_port}/healthz")
            if browser:
                if not (FRONTEND / ".output/server/index.mjs").exists():
                    raise RuntimeError("Run pnpm build in frontend before browser tests")
                launch("nuxt", [node, ".output/server/index.mjs"], FRONTEND,
                       {"HOST": "127.0.0.1", "PORT": str(frontend_port)})
            else:
                launch("nuxt", [node, "node_modules/nuxt/bin/nuxt.mjs", "dev", "--host", "127.0.0.1", "--port", str(frontend_port)], FRONTEND)
            wait(f"http://127.0.0.1:{frontend_port}/api/gateway/healthz")
            if browser:
                subprocess.run([node, "node_modules/@playwright/test/cli.js", "test"],
                               cwd=FRONTEND, env=env, check=True, timeout=600)
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
            if ai:
                ai.shutdown()
                ai.server_close()


if __name__ == "__main__":
    main()
