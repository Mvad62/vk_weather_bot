import sqlite3
from contextlib import closing
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "data" / "user_cities.sqlite3"


def get_city(user_id: int) -> str | None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH, timeout=10)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_cities (
                    user_id INTEGER PRIMARY KEY,
                    city TEXT NOT NULL
                )
                """
            )
            row = connection.execute(
                "SELECT city FROM user_cities WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    return row[0] if row else None


def set_city(user_id: int, city: str) -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH, timeout=10)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_cities (
                    user_id INTEGER PRIMARY KEY,
                    city TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO user_cities (user_id, city)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET city = excluded.city
                """,
                (user_id, city),
            )
