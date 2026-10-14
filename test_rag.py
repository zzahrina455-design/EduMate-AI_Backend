
from rag_service import cari_lomba_relevan


teks_proyek = """
Smart Robot Kit merupakan proyek robot edukasi untuk membantu
siswa sekolah dasar mempelajari teknologi, robotika, sensor,
pemrograman dasar, dan pembelajaran interaktif.
Proyek ini bertujuan meningkatkan kreativitas dan kemampuan
pemecahan masalah siswa melalui praktik langsung.
"""

try:
    hasil = cari_lomba_relevan(teks_proyek, jumlah=5)

    if not hasil:
        print("Belum ditemukan lomba relevan.")
        print("Pastikan database memiliki lomba dengan status aktif.")
    else:
        print(f"Jumlah lomba ditemukan: {len(hasil)}")

        for nomor, lomba in enumerate(hasil, start=1):
            print(f"\n--- Rekomendasi {nomor} ---")
            print("Nama lomba:", lomba["nama_lomba"])
            print("Kategori:", lomba["kategori"])
            print("Penyelenggara:", lomba["penyelenggara"])
            print("Persyaratan:", lomba["persyaratan"])
            print("Jarak semantik:", round(lomba["jarak"], 4))

except Exception as error:
    print("Pengujian RAG gagal.")
    print("Jenis error:", type(error).__name__)
    print("Pesan:", str(error))
