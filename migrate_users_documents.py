
import sqlite3
from sqlalchemy import inspect, text
from database import engine

SQLITE_FILE = "edumate.db"
TABLES = ["users", "dokumen_proyek"]

source = sqlite3.connect(SQLITE_FILE)
source.row_factory = sqlite3.Row

try:
    with engine.begin() as conn:
        inspector = inspect(conn)

        for table in TABLES:
            rows = source.execute(
                f'SELECT * FROM "{table}"'
            ).fetchall()

            pg_columns = {
                column["name"]
                for column in inspector.get_columns(table)
            }

            if not rows:
                print(f"{table}: tidak ada data untuk dipindahkan")
                continue

            columns = [
                column for column in rows[0].keys()
                if column in pg_columns
            ]

            inserted = 0
            skipped = 0

            for row in rows:
                data = {column: row[column] for column in columns}

                existing = conn.execute(
                    text(f'SELECT 1 FROM "{table}" WHERE id = :id'),
                    {"id": data["id"]}
                ).first()

                if existing:
                    skipped += 1
                    continue

                column_sql = ", ".join(f'"{c}"' for c in columns)
                value_sql = ", ".join(f":{c}" for c in columns)

                conn.execute(
                    text(
                        f'INSERT INTO "{table}" '
                        f'({column_sql}) VALUES ({value_sql})'
                    ),
                    data
                )
                inserted += 1

            print(
                f"{table}: {inserted} data dipindahkan, "
                f"{skipped} data dilewati"
            )

finally:
    source.close()
