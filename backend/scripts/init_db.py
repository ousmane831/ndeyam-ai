"""
Initialisation de la base PostgreSQL de NDEYAM AI.

Ce script :
  1. demande les identifiants d'un compte administrateur PostgreSQL (ex. « postgres ») ;
  2. crée, s'ils n'existent pas, un rôle dédié « ndeyamai » (LOGIN, CREATEDB) et une base « ndeyamai » ;
  3. écrit les paramètres de connexion dans backend/.env (créé depuis .env.example si absent).

Il ne modifie NI la configuration du serveur PostgreSQL (postgresql.conf, pg_hba.conf),
NI les autres bases ou rôles existants. Le mot de passe administrateur n'est jamais enregistré.
Le droit CREATEDB est nécessaire pour que les tests créent leur base temporaire « test_ndeyamai ».

Utilisation (depuis le dossier backend, environnement virtuel activé) :
    python scripts/init_db.py
"""

import getpass
import re
import secrets
import sys
from pathlib import Path

import psycopg
from psycopg import sql

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"
ENV_EXAMPLE = BACKEND_DIR / ".env.example"

DB_NAME = "ndeyamai"
DB_USER = "ndeyamai"


def ask(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}] : ").strip()
    return value or default


def read_env() -> str:
    if ENV_FILE.exists():
        return ENV_FILE.read_text(encoding="utf-8")
    return ENV_EXAMPLE.read_text(encoding="utf-8")


def set_env_value(content: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    line = f"{key}={value}"
    if pattern.search(content):
        return pattern.sub(lambda _m: line, content)
    return content.rstrip("\n") + f"\n{line}\n"


def get_env_value(content: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def main() -> int:
    print("=== Initialisation de la base PostgreSQL de NDEYAM AI ===\n")
    host = ask("Hôte PostgreSQL", "localhost")
    port = ask("Port", "5432")
    admin_user = ask("Utilisateur administrateur PostgreSQL", "postgres")
    admin_password = getpass.getpass(f"Mot de passe de « {admin_user} » (non enregistré) : ")

    env_content = read_env()
    app_password = get_env_value(env_content, "DB_PASSWORD") or secrets.token_urlsafe(24)

    try:
        with psycopg.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            dbname="postgres",
            autocommit=True,
            connect_timeout=10,
        ) as conn:
            role_exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (DB_USER,)).fetchone()
            if role_exists:
                print(f"- Le rôle « {DB_USER} » existe déjà : mise à jour de son mot de passe.")
                conn.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN CREATEDB PASSWORD {}").format(
                        sql.Identifier(DB_USER), sql.Literal(app_password)
                    )
                )
            else:
                conn.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN CREATEDB PASSWORD {}").format(
                        sql.Identifier(DB_USER), sql.Literal(app_password)
                    )
                )
                print(f"- Rôle « {DB_USER} » créé.")

            db_exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)).fetchone()
            if db_exists:
                print(f"- La base « {DB_NAME} » existe déjà : elle est conservée telle quelle.")
            else:
                conn.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(
                        sql.Identifier(DB_NAME), sql.Identifier(DB_USER)
                    )
                )
                print(f"- Base « {DB_NAME} » créée (propriétaire : {DB_USER}, encodage UTF-8).")
    except psycopg.OperationalError as exc:
        print(f"\nÉchec de la connexion à PostgreSQL : {exc}")
        return 1

    for key, value in {
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": app_password,
        "DB_HOST": host,
        "DB_PORT": port,
    }.items():
        env_content = set_env_value(env_content, key, value)

    secret = get_env_value(env_content, "DJANGO_SECRET_KEY")
    if not secret or secret.startswith("a-remplacer"):
        env_content = set_env_value(env_content, "DJANGO_SECRET_KEY", secrets.token_urlsafe(50))
        print("- Clé secrète Django générée.")

    ENV_FILE.write_text(env_content, encoding="utf-8")
    print(f"- Paramètres de connexion enregistrés dans {ENV_FILE}")
    print("\nTerminé. Étape suivante : python manage.py migrate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
