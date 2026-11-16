import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def connectionBD():
    try:
        return mysql.connector.connect(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"],
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            use_unicode=True,
            connection_timeout=5,
        )
    except (mysql.connector.Error, KeyError, ValueError) as exc:
        raise ConnectionError("No se pudo establecer la conexión con MySQL.") from exc
