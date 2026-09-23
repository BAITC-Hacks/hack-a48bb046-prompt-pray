#!/usr/bin/env python3
"""Генерирует случайные секреты для .env (особенно для production)."""
import secrets

SECRETS = [
    "JWT_SECRET_KEY",
    "POSTGRES_ADMIN_PASSWORD",
    "AUTH_DB_PASSWORD",
    "EXAMPLE_DB_PASSWORD",
]

if __name__ == "__main__":
    print("# Вставьте в .env, заменив dev-only значения:")
    for name in SECRETS:
        print(f"{name}={secrets.token_urlsafe(32)}")
