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


def is_valid_target_post(caption: str) -> bool:
    """
    Menyaring caption agar HANYA meloloskan:
    1. Kompetisi / Lomba / Hackathon / Challenge
    2. Pendanaan / Funding / Inkubasi / PKM
    3. Hibah / Grant / Call for Proposal
    Serta membuang pelatihan/webinar murni yang tidak ada unsur lomba.
    """
    text = caption.lower()

    # Kata kunci kategori target (Kompetisi, Pendanaan, Hibah)
    target_keywords = [
        "lomba",
        "competition",
        "kompetisi",
        "hackathon",
        "ui/ux",
        "web development",
        "infokompetisi",
        "gemastik",
        "olivia",
        "pln",
        "olimpiade",
        "festival",
        "vokasi",
        "tantangan",
        "national",
        "nasional",
        "code",
        "programming",
        "ai",
        "inovasi",
        "pendanaan",
        "hibah",
        "grant",
        "funding",
        "inkubasi",
        "pkm",
        "bantuan pendanaan",
        "championship",
        "call for proposal",
        "business plan",
        "pitching",
        "kompetisi nasional",
    ]

    # Cek apakah mengandung setidaknya satu kata kunci target
    has_target = any(kw in text for kw in target_keywords)

    # Filter pengecualian: Jika ini murni webinar/pelatihan biasa tolak
    is_pure_webinar_or_training = any(
        ex in text
        for ex in [
            "webinar",
            "pelatihan online",
            "workshop online",
            "kursus online",
            "bootcamp",
        ]
    ) and not any(
        k in text
        for k in [
            "lomba",
            "kompetisi",
            "hibah",
            "pendanaan",
            "grant",
            "pkm",
            "hackathon",
            "challenge",
        ]
    )

    return has_target and not is_pure_webinar_or_training


async def fetch_and_store_instagram_competitions(db: Session):
    if not APIFY_API_KEY:
        print("[APIFY ERROR] APIFY_API_KEY belum disetel di file .env!")
        return {"error": "API Key Apify belum dikonfigurasi"}

    client = ApifyClient(APIFY_API_KEY)

    target_urls = [
        "https://www.instagram.com/inforlomba/",
        "https://www.instagram.com/lombamahasiswa.id/",
        "https://www.instagram.com/infokompetisi/",
        "https://www.instagram.com/explore/tags/gemastik/",
        "https://www.instagram.com/explore/tags/oliviavokasi/",
        "https://www.instagram.com/explore/tags/pendanaandana/",
    ]

    print(
        "[APIFY] Menjalankan Instagram Scraper Actor (Filter: Kompetisi)..."
    )

    try:
        run = client.actor("apify/instagram-scraper").call(
            run_input={
                "directUrls": target_urls,
                "resultsLimit": 1000,  # Batas maksimal penarikan data
                "searchType": "user",
                "searchLimit": 1,
            }
        )

        dataset_id = None
        if hasattr(run, "default_dataset_id"):
            dataset_id = run.default_dataset_id
        if not dataset_id and hasattr(run, "defaultDatasetId"):
            dataset_id = run.defaultDatasetId
        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get(
                "default_dataset_id") or run.get("defaultDatasetId")
        if not dataset_id:
            try:
                run_dict = dict(run)
                dataset_id = run_dict.get(
                    "default_dataset_id") or run_dict.get("defaultDatasetId")
            except Exception:
                pass

        if not dataset_id:
            raise ValueError(
                "Gagal mendapatkan default_dataset_id dari hasil eksekusi."
            )

        dataset_items = client.dataset(dataset_id).iterate_items()

        new_count = 0
        for item in dataset_items:
            raw_caption = item.get("caption", "")
            caption = clean_text(raw_caption)
            post_url = item.get("url", "")

            # Gunakan fungsi filter ketat
            if is_valid_target_post(caption):
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
                        else "Kompetisi & Pendanaan Mahasiswa"
                    )

                    new_comp = Competition(
                        title=title,
                        description=caption[:1000],
                        requirements="Cek detail persyaratan pada link",
                        deadline=datetime.utcnow(),
                        social_media_link=post_url,
                    )
                    db.add(new_comp)
                    new_count += 1

        db.commit()
        print(
            f"[APIFY SUCCESS] Berhasil menyimpan {new_count} data baru"
        )
        return {"message": f"Berhasil sinkronisasi {new_count} data baru."}

    except Exception as e:
        print(f"[APIFY ERROR] Gagal melakukan scraping Instagram: {str(e)}")
        return {"error": str(e)}
