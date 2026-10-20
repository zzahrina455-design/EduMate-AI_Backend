import os
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# Model prioritas utama untuk Chat / RAG
PRIORITY_MODELS = [
    "llama-3.3-70b-specdec",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "llama-3.2-11b-vision-preview"
]

def get_filtered_groq_models():
    """
    Mengambil model aktif dari Groq dan memfilter hanya model Chat/RAG yang valid.
    """
    try:
        models_page = client.models.list()
        # Ambil semua ID model yang aktif
        all_active = [m.id for m in models_page.data if getattr(m, 'active', True)]
        
        # Kata kunci model yang WAJIB DIABAIKAN (bukan model chat umum)
        ignored_keywords = [
            "safeguard", "guard", "whisper", "orpheus", "allam", 
            "audio", "vision", "embed", "prompt-guard"
        ]

        valid_models = []
        # Utamakan model prioritas utama terlebih dahulu jika ada di daftar aktif
        for pm in PRIORITY_MODELS:
            if pm in all_active and pm not in valid_models:
                valid_models.append(pm)

        # Tambahkan model aktif lainnya yang lolos filter
        for model_id in all_active:
            if model_id not in valid_models:
                if not any(keyword in model_id.lower() for keyword in ignored_keywords):
                    valid_models.append(model_id)

        if valid_models:
            return valid_models
    except Exception as e:
        print(f"[GROQ MODEL FETCH WARNING] Gagal mengambil list model: {e}")

    return PRIORITY_MODELS

def call_openrouter(prompt: str, system_prompt: str = "") -> str:
    """
    Fungsi eksekusi LLM Groq dengan pemfilteran model RAG yang ketat.
    """
    models_to_try = get_filtered_groq_models()
    last_error = ""

    for model_name in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_completion_tokens=2048,
                top_p=1,
                stream=False,
            )
            print(f"[GROQ LLM SUCCESS] Berhasil menggunakan model aktif: {model_name}")
            return completion.choices[0].message.content

        except Exception as e:
            last_error = str(e)
            print(f"[GROQ LLM NOTICE] Model '{model_name}' gagal ({e}). Mencoba model berikutnya...")

    return f"Error LLM Service (Groq): {last_error}"