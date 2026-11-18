"""Siembra en app_user los correos de FIREBASE_ADMIN_EMAILS para que puedan atender alertas.

Marcar una alerta como atendida (POST /alerts/{id}/handle) guarda QUIÉN la atendió, así que el correo
verificado de quien inició sesión con Firebase debe existir en app_user; si no, responde 403
("Your login has no verified email registered in app_user"). La base nueva trae app_user y app_role vacías.

El login es de Firebase: password_hash no se usa para autenticar, así que se guarda un valor que no
coincide con ningún hash. Solo se siembran correos que YA están autorizados como administradores del
panel (FIREBASE_ADMIN_EMAILS); no se crea ningún acceso nuevo.

Es idempotente: el rol y los usuarios que ya existen se dejan como están.

    docker compose exec monolito-escucha python -m scripts.seed_admin_users
"""
from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

ADMIN_ROLE = "admin"
UNUSABLE_PASSWORD_HASH = "!firebase-login"  # no es un hash válido: nadie puede entrar con contraseña


def admin_emails() -> list[str]:
    emails = [item.strip().lower() for item in settings.firebase_admin_emails.split(",") if item.strip()]
    return list(dict.fromkeys(emails))


async def seed(emails: list[str]) -> list[tuple[str, bool]]:
    engine = create_async_engine(settings.database_url)
    rows: list[tuple[str, bool]] = []
    try:
        async with engine.begin() as con:
            role_code = (await con.execute(
                text("SELECT role_code FROM app_role WHERE name = :n"), {"n": ADMIN_ROLE})).scalar()
            if role_code is None:
                role_code = (await con.execute(
                    text("INSERT INTO app_role (name) VALUES (:n) RETURNING role_code"),
                    {"n": ADMIN_ROLE})).scalar_one()

            for email in emails:
                exists = (await con.execute(
                    text("SELECT 1 FROM app_user WHERE lower(email) = :e"), {"e": email})).scalar()
                if not exists:
                    await con.execute(
                        text("INSERT INTO app_user (email, full_name, password_hash, is_active, role_code) "
                             "VALUES (:e, :n, :p, true, :r)"),
                        {"e": email, "n": email.split("@")[0], "p": UNUSABLE_PASSWORD_HASH, "r": role_code})
                rows.append((email, not exists))
    finally:
        await engine.dispose()
    return rows


def mask(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}"


def main() -> None:
    emails = admin_emails()
    if not emails:
        print("FIREBASE_ADMIN_EMAILS está vacío: no hay usuarios que sembrar.")
        return
    for email, created in asyncio.run(seed(emails)):
        print(f"{mask(email)}: {'creado' if created else 'ya existía'} (rol {ADMIN_ROLE})")


if __name__ == "__main__":
    main()
