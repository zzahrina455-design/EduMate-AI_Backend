
from database import SessionLocal
import models

db = SessionLocal()

try:
    lomba = (
        db.query(models.Competition)
        .filter(models.Competition.id == 3)
        .first()
    )

    if lomba:
        lomba.status = "nonaktif"
        db.commit()
        print("Berhasil menonaktifkan data template ID 3.")
        print("Nama lomba:", lomba.name)
        print("Status terbaru:", lomba.status)
    else:
        print("Data lomba ID 3 tidak ditemukan.")

finally:
    db.close()
