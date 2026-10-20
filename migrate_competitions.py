
import sqlite3
from sqlalchemy import inspect, text
from database import engine

# Baca data dari database SQLite lama
source = sqlite3.connect("edumate.db")
source.row_factory = sqlite3.Row

try:
    rows = source.execute(
        "SELECT * FROM competitions ORDER BY id"
    ).fetchall()

    if not rows:
        print("Tidak ada data lomba di SQLite.")
        raise SystemExit(0)

    inspector = inspect(engine)
    if "competitions" not in inspector.get_table_names():
        raise RuntimeError("Tabel competitions tidak ditemukan.")

    target_columns = {
        column["name"]
        for column in inspector.get_columns("competitions")
    }

    common_columns = [
        column for column in rows[0].keys()
        if column in target_columns
    ]

    inserted = 0
    skipped = 0

    with engine.begin() as connection:
        for row in rows:
            existing = connection.execute(
                text("SELECT 1 FROM competitions WHERE id = :id"),
                {"id": row["id"]}
            ).first()

            if existing:
                skipped += 1
                continue

            values = {
                column: row[column]
                for column in common_columns
            }

            columns_sql = ", ".join(
                f'"{column}"' for column in common_columns
            )
            params_sql = ", ".join(
                f":{column}" for column in common_columns
            )

            connection.execute(
                text(
                    f"INSERT INTO competitions "
                    f"({columns_sql}) VALUES ({params_sql})"
                ),
                values
            )
            inserted += 1

    print("Jumlah data SQLite:", len(rows))
    print("Data baru dipindahkan:", inserted)
    print("Data dilewati karena ID sudah ada:", skipped)

finally:
    source.close()
