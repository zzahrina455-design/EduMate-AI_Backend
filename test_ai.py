
from rag_service import cari_lomba_relevan
from ai_service import analisis_kecocokan_proyek


teks_proyek = """
Smart Robot Kit merupakan proyek robot edukasi untuk membantu
siswa sekolah dasar mempelajari teknologi, robotika, sensor,
pemrograman dasar, dan pembelajaran interaktif.

Proyek ini bertujuan meningkatkan kreativitas dan kemampuan
pemecahan masalah siswa melalui praktik langsung.
"""


try:
    print("1. Mencari lomba menggunakan RAG...")

    daftar_lomba = cari_lomba_relevan(
        teks_proyek,
        jumlah=5,
    )

    if not daftar_lomba:
        print("Belum ada lomba aktif di database.")
    else:
        print(f"Lomba ditemukan: {len(daftar_lomba)}")
        print("\n2. Meminta Mercury menganalisis kecocokan...")

        hasil = analisis_kecocokan_proyek(
            teks_proyek,
            daftar_lomba,
        )

        print("\n=== HASIL ANALISIS MERCURY ===")

        for nomor, item in enumerate(hasil, start=1):
            print(f"\nRekomendasi {nomor}")
            print("ID lomba:", item["competition_id"])
            print("Alasan:", item["alasan_kecocokan"])

            print("Kelebihan proyek:")
            for kelebihan in item["kelebihan_proyek"]:
                print("-", kelebihan)

            print("Kekurangan proyek:")
            for kekurangan in item["kekurangan_proyek"]:
                print("-", kekurangan)

except Exception as error:
    print("\nPengujian gagal.")
    print("Jenis error:", type(error).__name__)
    print("Pesan:", str(error))
