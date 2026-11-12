import os
from apify_client import ApifyClient
from sqlalchemy.orm import Session
from app.models.models import Competition
from datetime import datetime

APIFY_API_KEY = os.getenv("APIFY_API_KEY")


def clean_text(text: str) -> str:
    """Membersihkan teks dari byte UTF-8 yang rusak/tidak valid."""
    if not text:
        return ""
    return text.encode("utf-8", "ignore").decode("utf-8")


def calculate_match_probability(caption: str) -> int:
    """
    Menghitung persentase peluang relevansi/kecocokan (probability score)
    berdasarkan bobot kata kunci teknologi (IT, IoT, AI, Hackathon, dll.).
    Hanya meloloskan kompetisi dengan peluang > 50%.
    """
    text = caption.lower()

    # Daftar kata kunci terlarang (Webinar / Kelas / Non-lomba mutlak ditolak)
    excluded_keywords = [
        "webinar",
        "kelas online",
        "kelas gratis",
        "workshop",
        "seminar",
        "talkshow",
        "sosialisasi",
        "pelatihan",
        "bootcamp",
        "kursus",
        "bimbingan belajar",
        "sharing session",
        "podcast",
        "duta kampus",
        "duta inspirasi",
        "pemilihan duta",
        "lomba baca puisi",
        "lomba menyanyi",
    ]
    if any(ex in text for ex in excluded_keywords):
        return 0  # Peluang 0% (ditolak)

    # Kata kunci primer berbobot tinggi (Teknologi / IoT / AI / Sistem)
    primary_tech = [
        "iot",
        "ai",
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "hackathon",
        "gemastik",
        "robotik",
        "smart agriculture",
        "smart farming",
        "smart city",
        "sensor",
        "esp32",
        "arduino",
        "microcontroller",
    ]

    # Kata kunci sekunder (IT umum / Software / Development / Pendanaan)
    secondary_tech = [
        "it",
        "ui/ux",
        "web development",
        "app development",
        "software",
        "hardware",
        "programming",
        "code",
        "coding",
        "data science",
        "cyber security",
        "cloud",
        "automation",
        "sistem informasi",
        "teknik informatika",
        "informatika",
        "digital",
        "startup",
    ]

    # Kata kunci jenis event kompetisi/pendanaan
    event_keywords = [
        "lomba",
        "competition",
        "kompetisi",
        "challenge",
        "championship",
        "call for proposal",
        "pendanaan",
        "hibah",
        "grant",
        "funding",
        "inkubasi",
        "pkm",
    ]

    # Cek apakah ada jenis event lomba/pendanaan
    has_event = any(kw in text for kw in event_keywords)
    if not has_event:
        return 20  # Bukan kompetisi, peluang rendah

    # Hitung skor berdasarkan kemunculan kata kunci
    score = 40  # Base score jika lolos sebagai event

    # Tambah bobot jika mengandung teknologi primer (IoT/AI/Hackathon/Gemastik)
    primary_matches = sum(1 for kw in primary_tech if kw in text)
    if primary_matches > 0:
        score += min(primary_matches * 25, 45)  # Bisa menambah hingga +45%

    # Tambah bobot jika mengandung teknologi sekunder
    secondary_matches = sum(1 for kw in secondary_tech if kw in text)
    if secondary_matches > 0:
        score += min(secondary_matches * 15, 30)  # Bisa menambah hingga +30%

    # Batasi maksimal 98%
    return min(score, 98)


async def fetch_and_store_instagram_competitions(db: Session):
    if not APIFY_API_KEY:
        print("[APIFY ERROR] APIFY_API_KEY belum disetel di file .env!")
        return {"error": "API Key Apify belum dikonfigurasi"}

    client = ApifyClient(APIFY_API_KEY)

    target_urls = [
        "https://www.instagram.com/infokompetisi/",
        "https://www.instagram.com/lombamahasiswa.id/",
        "https://www.instagram.com/explore/tags/gemastik/",
        "https://www.instagram.com/explore/tags/lombait/",
        "https://www.instagram.com/explore/tags/hackathonindonesia/",
        "https://www.instagram.com/explore/tags/iotindonesia/",
    ]

    print("[APIFY] Menjalankan Instagram Scraper (Filter Probability > 50%)...")

    try:
        run = client.actor("apify/instagram-scraper").call(
            run_input={
                "directUrls": target_urls,
                "resultsLimit": 150,
            }
        )

        dataset_id = None
        if hasattr(run, "default_dataset_id"):
            dataset_id = run.default_dataset_id
        if not dataset_id and hasattr(run, "defaultDatasetId"):
            dataset_id = run.defaultDatasetId
        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get("default_dataset_id") or run.get("defaultDatasetId")
        if not dataset_id:
            try:
                run_dict = dict(run)
                dataset_id = run_dict.get("default_dataset_id") or run_dict.get(
                    "defaultDatasetId"
                )
            except Exception:
                pass

        if not dataset_id:
            raise ValueError(
                "Gagal mendapatkan default_dataset_id dari hasil eksekusi."
            )

        dataset_items = client.dataset(dataset_id).iterate_items()

        new_count = 0
        skipped_count = 0

        for item in dataset_items:
            try:
                raw_caption = item.get("caption", "")
                caption = clean_text(raw_caption)
                post_url = item.get("url", "")

                if not post_url or not caption:
                    continue

                # Hitung peluang/probabilitas lolos
                probability = calculate_match_probability(caption)

                # SYARAT UTAMA: Hanya ambil yang peluangnya > 50%
                if probability > 50:
                    existing = (
                        db.query(Competition)
                        .filter(Competition.social_media_link == post_url)
                        .first()
                    )

                    if not existing:
                        title_lines = caption.split("\n")
                        title = (
                            clean_text(title_lines[0][:100])
                            if title_lines
                            else "Kompetisi IT & Inovasi Digital"
                        )

                        new_comp = Competition(
                            title=title,
                            description=caption[:1000],
                            requirements=f"Estimasi Peluang Relevansi: {probability}%. Cek detail persyaratan lengkap pada tautan sumber.",
                            deadline=datetime.utcnow(),
                            social_media_link=post_url,
                        )
                        db.add(new_comp)
                        db.commit()  # Simpan per item secara aman agar proses refresh tidak stuck
                        new_count += 1
                else:
                    skipped_count += 1

            except Exception as item_err:
                db.rollback()
                print(f"[APIFY WARNING] Gagal memproses item post: {str(item_err)}")
                continue

        print(
            f"[APIFY SUCCESS] Refresh selesai. Menambahkan {new_count} kompetisi baru (>50% match). Dilewati: {skipped_count} postingan."
        )
        return {
            "message": f"Berhasil refresh! Menambahkan {new_count} kompetisi IT baru ke database."
        }

    except Exception as e:
        db.rollback()
        print(f"[APIFY ERROR] Gagal melakukan scraping Instagram: {str(e)}")
        return {"error": str(e)}
