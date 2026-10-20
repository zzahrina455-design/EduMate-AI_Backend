import os
from pypdf import PdfReader
from docx import Document
from PIL import Image

def extract_text_from_file(file_path: str, file_extension: str) -> str:
    """
    Mengekstrak teks dari file PDF, DOCX, TXT, atau Gambar.
    """
    ext = file_extension.lower()
    extracted_text = ""

    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"

        elif ext in [".docx", ".doc"]:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    extracted_text += paragraph.text + "\n"

        elif ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                extracted_text = f.read()

        elif ext in [".jpg", ".jpeg", ".png"]:
            # Catatan: Teks gambar disederhanakan sebagai penanda konteks gambar
            extracted_text = f"[Gambar Diunggah: {os.path.basename(file_path)}]"

    except Exception as e:
        print(f"[DOCUMENT PARSE ERROR] Gagal mengekstrak {file_path}: {e}")

    return extracted_text.strip()