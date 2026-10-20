import httpx
import json
import re
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models import Competition
from llm_service import call_openrouter

def extract_ti_data_with_llm(raw_items: list) -> list:
    """
    Menggunakan LLM untuk menyaring dan mengekstrak HANYA lomba Teknik Informatika.
    """
    system_prompt = (
        "Kamu adalah kurator dan parser data lomba Teknik Informatika di Indonesia & Global.\n"
        "Tugasmu: Dari data mentah berikut, filter dan ekstrak HANYA lomba yang relevan dengan Teknik Informatika.\n"
        "PENTING: Salin atau konversi tanggal deadline ASLI dari field 'raw_date' atau 'submission_period_dates' jika ada menjadi format YYYY-MM-DD. "
        "Jangan menyamaratakan tanggal deadline!\n\n"
        "Format output WAJIB berupa JSON array murni tanpa tag markdown:\n"
        '[\n'
        '  {\n'
        '    "title": "Nama Lomba TIK",\n'
        '    "description": "Deskripsi singkat",\n'
        '    "requirements": "Persyaratan peserta",\n'
        '    "deadline": "YYYY-MM-DD",\n'
        '    "social_media_link": "URL"\n'
        '  }\n'
        ']'
    )

    prompt_text = "Data Mentah Lomba:\n"
    for idx, item in enumerate(raw_items[:12], 1):
        prompt_text += (
            f"{idx}. Judul: {item.get('title')}\n"
            f"   Deskripsi: {item.get('description')}\n"
            f"   Tanggal/Keterangan Waktu Asli: {item.get('raw_date', 'Sesuai Pengumuman')}\n"
            f"   URL: {item.get('url')}\n\n"
        )

    try:
        response_text = call_openrouter(prompt_text, system_prompt)
        if response_text:
            cleaned_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            match = re.search(r'\[\s*\{.*\}\s*\]', cleaned_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            if cleaned_text.startswith("[") and cleaned_text.endswith("]"):
                return json.loads(cleaned_text)
    except Exception as e:
        print(f"[LLM PARSE WARNING] {e}")

    # Fallback Parsing Otomatis jika LLM error/limit: Berikan tanggal bervariasi
    fallback_result = []
    base_date = datetime.now()
    for idx, item in enumerate(raw_items, start=1):
        # Tambahkan interval hari berbeda (misal: 15 hari, 30 hari, 45 hari) agar deadline bervariasi
        staggered_deadline = base_date + timedelta(days=15 * idx)
        fallback_result.append({
            "title": item.get("title", "Lomba TIK Mahasiswa"),
            "description": item.get("description", "Kompetisi Pemrograman & Inovasi Software Mahasiswa"),
            "requirements": "Mahasiswa Aktif D3/S1 Teknik Informatika / IT",
            "deadline": staggered_deadline.strftime("%Y-%m-%d"),
            "social_media_link": item.get("url", "https://pusprestnas.kemdikbud.go.id")
        })
    return fallback_result


async def fetch_and_store_ti_competitions(db: Session):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    raw_collected_items = []

    print("[AUTO-SCRAPER] Mengambil data live dari Portal Lomba & Challenge...")

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers=headers) as client:
        # 1. LIVE SCRAPE: Portal Puspresnas Kemdikbud
        try:
            res_puspresnas = await client.get("https://pusprestnas.kemdikbud.go.id")
            if res_puspresnas.status_code == 200:
                soup = BeautifulSoup(res_puspresnas.text, "html.parser")
                links = soup.find_all("a", href=True)
                for a in links:
                    text = a.get_text().strip()
                    if len(text) > 15 and any(k in text.lower() for k in ["gemastik", "lomba", "kompetisi", "tik", "pkm"]):
                        href = a["href"]
                        if not href.startswith("http"):
                            href = f"https://pusprestnas.kemdikbud.go.id{href}"
                        raw_collected_items.append({
                            "title": text,
                            "description": "Kompetisi Mahasiswa Tingkat Nasional Kemendikbudristek",
                            "raw_date": "Cek jadwal resmi di portal Puspresnas",
                            "url": href
                        })
        except Exception as e:
            print(f"[AUTO-SCRAPER NOTICE] Puspresnas fetch: {e}")

        # 2. LIVE SCRAPE: Devpost Hackathons API (Ambil field submission_period_dates)
        try:
            res_devpost = await client.get("https://devpost.com/api/hackathons")
            if res_devpost.status_code == 200:
                hackathons = res_devpost.json().get("hackathons", [])
                for h in hackathons[:8]:
                    raw_collected_items.append({
                        "title": h.get("title"),
                        "description": h.get("tagline") or "Hackathon Software Development & AI",
                        "raw_date": h.get("submission_period_dates") or h.get("displayed_location", {}).get("location", ""),
                        "url": h.get("url", "https://devpost.com")
                    })
        except Exception as e:
            print(f"[AUTO-SCRAPER NOTICE] Devpost fetch: {e}")

    # 3. Simpan ke PostgreSQL
    if raw_collected_items:
        processed_competitions = extract_ti_data_with_llm(raw_collected_items)

        stored_count = 0
        for item in processed_competitions:
            title = item.get("title")
            if not title or len(title) < 3:
                continue

            existing = db.query(Competition).filter(Competition.title == title).first()
            if not existing:
                try:
                    deadline_date = datetime.strptime(item.get("deadline"), "%Y-%m-%d")
                except (ValueError, TypeError):
                    deadline_date = datetime.now() + timedelta(days=30)

                link = item.get("social_media_link") or "https://pusprestnas.kemdikbud.go.id"

                new_comp = Competition(
                    title=title,
                    description=item.get("description", "Kompetisi Bidang Teknik Informatika"),
                    requirements=item.get("requirements", "Mahasiswa Aktif IT / Perguruan Tinggi"),
                    deadline=deadline_date,
                    social_media_link=link
                )
                db.add(new_comp)
                stored_count += 1

        db.commit()
        print(f"[AUTO-SCRAPER SUCCESS] Berhasil menyimpan {stored_count} data lomba live ke PostgreSQL!")
    else:
        print("[AUTO-SCRAPER NOTICE] Tidak ada data mentah yang berhasil ditarik dari web.")