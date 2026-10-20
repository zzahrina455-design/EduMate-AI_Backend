
import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("INCEPTION_API_KEY")
BASE_URL = os.getenv(
    "INCEPTION_BASE_URL",
    "https://api.inceptionlabs.ai/v1",
)
MODEL = os.getenv("INCEPTION_MODEL", "mercury-2.5")

if not API_KEY:
    raise ValueError(
        "INCEPTION_API_KEY belum diatur di file .env."
    )

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)


def analisis_kecocokan_proyek(teks_proyek, daftar_lomba):
    """
    Menganalisis kecocokan proyek dengan lomba menggunakan
    Mercury 2.5 berdasarkan kandidat hasil pencarian RAG.
    """

    if not teks_proyek or not teks_proyek.strip():
        raise ValueError("Teks proyek tidak boleh kosong.")

    if not daftar_lomba:
        return []

    konteks_lomba = []

    for lomba in daftar_lomba:
        konteks_lomba.append({
            "competition_id": lomba["competition_id"],
            "nama_lomba": lomba["nama_lomba"],
            "penyelenggara": lomba.get("penyelenggara"),
            "kategori": lomba["kategori"],
            "deskripsi": lomba["deskripsi"],
            "persyaratan": lomba.get("persyaratan"),
            "tautan_pendaftaran": lomba.get("tautan_pendaftaran"),
            "sumber": lomba.get("sumber"),
        })

    prompt = f"""
Kamu adalah asisten AI EduMate AI yang membantu mahasiswa
menilai kecocokan proyek dengan kompetisi.

DATA PROYEK:
{teks_proyek}

DATA LOMBA:
{json.dumps(konteks_lomba, ensure_ascii=False, indent=2)}

TUGAS:
Analisis setiap lomba hanya berdasarkan data proyek dan data
lomba yang diberikan.

Beri skor kecocokan berupa bilangan bulat 0 sampai 100:
- 80-100: Sangat cocok, hubungan langsung dan kuat.
- 60-79: Cocok, terdapat hubungan yang jelas.
- 40-59: Cukup cocok, tetapi membutuhkan pengembangan.
- 20-39: Kurang cocok, hubungan terbatas.
- 0-19: Tidak cocok, hampir tidak ada hubungan langsung.

PEDOMAN:
1. Nilai kesesuaian kategori dan tujuan utama proyek.
2. Jangan menganggap sensor atau perangkat elektronik otomatis
   sebagai IoT jika tidak ada bukti konektivitas jaringan.
3. Jangan menganggap suatu proyek cocok untuk hackathon tanpa
   mempertimbangkan unsur pengembangan solusi atau perangkat lunak.
4. Jangan menganggap perangkat keras sebagai proyek UI/UX,
   animasi, atau desain visual tanpa bukti pendukung.
5. Jangan menaikkan skor hanya karena proyek masih bisa dikembangkan.
6. Jelaskan alasan kecocokan secara spesifik dan jujur.
7. Sebutkan kelebihan proyek yang didukung dokumen.
8. Sebutkan kekurangan atau informasi yang masih dibutuhkan.
9. Jangan mengarang persyaratan, tenggat, biaya, atau fakta lomba.
10. Jika informasi tidak tersedia, nyatakan bahwa informasi tersebut
    belum tersedia.
11. Pertahankan competition_id persis seperti data yang diberikan.
12. Berikan satu hasil untuk setiap lomba yang diberikan.
13. Urutkan dari skor tertinggi ke terendah.
14. Skor adalah estimasi analisis AI, bukan nilai resmi penyelenggara
    atau jaminan diterima dalam lomba.

KELUARAN:
Kembalikan hanya array JSON valid dengan format:
[
  {{
    "competition_id": 6,
    "skor_kecocokan": 85,
    "tingkat_kecocokan": "Sangat cocok",
    "alasan_kecocokan": "Alasan yang didukung data",
    "kelebihan_proyek": [
      "Kelebihan yang didukung data"
    ],
    "kekurangan_proyek": [
      "Kekurangan atau informasi yang belum tersedia"
    ]
  }}
]

Contoh di atas hanya contoh struktur, bukan hasil penilaian.
Jangan menyalin skor contoh secara otomatis.
Jangan tambahkan markdown atau teks di luar JSON.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Kamu adalah analis kecocokan proyek dan lomba "
                    "yang teliti, objektif, dan tidak mengarang fakta. "
                    "Kembalikan JSON valid sesuai instruksi."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=3000,
        reasoning_effort="low",
    )

    jawaban = response.choices[0].message.content

    if not jawaban:
        raise ValueError(
            "Mercury tidak memberikan hasil analisis."
        )

    jawaban = jawaban.strip()

    if jawaban.startswith("```"):
        baris = jawaban.splitlines()

        if baris and baris[0].startswith("```"):
            baris = baris[1:]

        if baris and baris[-1].strip() == "```":
            baris = baris[:-1]

        jawaban = "\n".join(baris).strip()

    try:
        hasil = json.loads(jawaban)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Mercury menghasilkan format JSON yang tidak valid."
        ) from error

    if not isinstance(hasil, list):
        raise ValueError(
            "Hasil analisis harus berupa array JSON."
        )

    hasil_valid = []
    id_valid = {
        lomba["competition_id"]
        for lomba in daftar_lomba
    }
    id_diproses = set()

    for item in hasil:
        if not isinstance(item, dict):
            continue

        competition_id = item.get("competition_id")
        skor = item.get("skor_kecocokan")
        alasan = item.get("alasan_kecocokan")
        kelebihan = item.get("kelebihan_proyek")
        kekurangan = item.get("kekurangan_proyek")

        if competition_id not in id_valid:
            continue

        if competition_id in id_diproses:
            continue

        if (
            not isinstance(skor, int)
            or isinstance(skor, bool)
            or not 0 <= skor <= 100
        ):
            continue

        if not isinstance(alasan, str) or not alasan.strip():
            continue

        if not isinstance(kelebihan, list):
            continue

        if not isinstance(kekurangan, list):
            continue

        if skor >= 80:
            tingkat = "Sangat cocok"
        elif skor >= 60:
            tingkat = "Cocok"
        elif skor >= 40:
            tingkat = "Cukup cocok"
        elif skor >= 20:
            tingkat = "Kurang cocok"
        else:
            tingkat = "Tidak cocok"

        hasil_valid.append({
            "competition_id": competition_id,
            "skor_kecocokan": skor,
            "tingkat_kecocokan": tingkat,
            "alasan_kecocokan": alasan.strip(),
            "kelebihan_proyek": [
                str(teks) for teks in kelebihan
            ],
            "kekurangan_proyek": [
                str(teks) for teks in kekurangan
            ],
        })

        id_diproses.add(competition_id)

    hasil_valid.sort(
        key=lambda item: item["skor_kecocokan"],
        reverse=True,
    )

    return hasil_valid


def jawab_pertanyaan_chat(pertanyaan: str) -> str:
    """
    Menjawab pertanyaan umum mahasiswa menggunakan Mercury.
    """

    pertanyaan = pertanyaan.strip()

    if not pertanyaan:
        raise ValueError("Pertanyaan tidak boleh kosong.")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Kamu adalah EduMate AI, asisten belajar mahasiswa. "
                    "Jawab menggunakan bahasa Indonesia yang ramah, "
                    "jelas, dan mudah dipahami. "
                    "Jelaskan konsep secara bertahap jika diperlukan. "
                    "Jika tidak mengetahui fakta, sampaikan dengan jujur. "
                    "Jangan mengarang sumber atau referensi."
                ),
            },
            {
                "role": "user",
                "content": pertanyaan,
            },
        ],
        max_tokens=1500,
        reasoning_effort="low",
    )

    jawaban = response.choices[0].message.content

    if not jawaban or not jawaban.strip():
        raise RuntimeError("AI tidak menghasilkan jawaban.")

    return jawaban.strip()
