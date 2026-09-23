#!/usr/bin/env python3
"""
Запускает pytest в каждом сервисе по отдельности.

Раздельно — потому что во всех сервисах пакет называется `app`,
и в одном процессе pytest их модули конфликтовали бы.

    pip install -r requirements-dev.txt
    python scripts/run_tests.py            # все сервисы
    python scripts/run_tests.py auth_service -k login
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ["api_gateway", "auth_service", "example_service", "ai_service", "catalog_service"]

if __name__ == "__main__":
    args = sys.argv[1:]
    selected = [args.pop(0)] if args and args[0] in SERVICES else SERVICES

    failed = []
    for service in selected:
        print(f"\n=== {service} ===", flush=True)
        test_dir = ROOT / service / "tests"
        if not test_dir.exists() or not any(test_dir.rglob("test_*.py")):
            print("Нет тестов — пропущено", flush=True)
            continue
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", *args], cwd=ROOT / service)
        if result.returncode != 0:
            failed.append(service)

    if failed:
        print(f"\nТесты упали: {', '.join(failed)}")
        sys.exit(1)
    print("\nВсе тесты прошли")
