
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("INCEPTION_API_KEY")
base_url = os.getenv("INCEPTION_BASE_URL")
model = os.getenv("INCEPTION_MODEL")

if not api_key or not base_url or not model:
    raise ValueError(
        "Konfigurasi Inception belum lengkap. Periksa file .env."
    )

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    "Jawab singkat dalam bahasa Indonesia, "
                    "maksimal 3 kalimat. Apa fungsi LLM dalam "
                    "sistem rekomendasi lomba?"
                ),
            }
        ],
        max_tokens=1000,
        reasoning_effort="low",
    )

    pilihan = response.choices[0]
    jawaban = pilihan.message.content

    print("Model:", response.model)
    print("Status:", pilihan.finish_reason)

    if jawaban:
        print("\nJawaban Mercury:")
        print(jawaban)
    else:
        print(
            "\nJawaban teks masih kosong. "
            "Periksa status dan detail respons berikut:"
        )
        print(response.model_dump_json(indent=2))

except Exception as error:
    print("Pengujian API gagal.")
    print("Jenis error:", type(error).__name__)
    print("Pesan:", str(error))
