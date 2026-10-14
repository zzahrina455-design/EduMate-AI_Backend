
import os

import chromadb
from sentence_transformers import SentenceTransformer

from database import SessionLocal
import models


# Folder penyimpanan indeks RAG
RAG_DIR = os.path.join("data", "chroma")
os.makedirs(RAG_DIR, exist_ok=True)

# Model embedding multibahasa
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Inisialisasi model dan vector database
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

chroma_client = chromadb.PersistentClient(path=RAG_DIR)

collection = chroma_client.get_or_create_collection(
    name="edumate_lomba",
    metadata={"hnsw:space": "cosine"},
)


def buat_teks_lomba(lomba):
    """Menggabungkan informasi lomba menjadi teks untuk pencarian."""
    return "\n".join([
        f"Nama lomba: {lomba.name or ''}",
        f"Penyelenggara: {lomba.organizer or ''}",
        f"Kategori: {lomba.category or ''}",
        f"Deskripsi: {lomba.description or ''}",
        f"Persyaratan: {lomba.requirements or ''}",
        f"Status: {lomba.status or ''}",
    ])


def sinkronkan_data_lomba():
    """
    Mengambil lomba aktif dari SQLite dan memperbarui indeks ChromaDB.
    Jalankan kembali fungsi ini setelah data lomba berubah.
    """
    db = SessionLocal()

    try:
        daftar_lomba = (
            db.query(models.Competition)
            .filter(models.Competition.status == "aktif")
            .all()
        )

        # Hapus indeks lama agar data yang tidak aktif
        # atau sudah dihapus tidak ikut direkomendasikan.
        data_lama = collection.get()

        if data_lama["ids"]:
            collection.delete(ids=data_lama["ids"])

        if not daftar_lomba:
            return 0

        ids = []
        documents = []
        metadatas = []

        for lomba in daftar_lomba:
            ids.append(str(lomba.id))
            documents.append(buat_teks_lomba(lomba))
            metadatas.append({
                "competition_id": lomba.id,
                "name": lomba.name or "",
                "category": lomba.category or "Umum",
                "organizer": lomba.organizer or "",
                "requirements": lomba.requirements or "",
                "description": lomba.description or "",
                "registration_url": lomba.registration_url or "",
                "source_url": lomba.source_url or "",
            })

        embeddings = embedding_model.encode(
            documents,
            normalize_embeddings=True,
        ).tolist()

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return len(ids)

    finally:
        db.close()


def cari_lomba_relevan(teks_proyek, jumlah=5):
    """Mencari lomba yang paling relevan dengan isi dokumen proyek."""
    if not teks_proyek or not teks_proyek.strip():
        return []

    # Pastikan indeks mengikuti data terbaru di database.
    sinkronkan_data_lomba()

    if collection.count() == 0:
        return []

    embedding_proyek = embedding_model.encode(
        [teks_proyek],
        normalize_embeddings=True,
    ).tolist()

    hasil = collection.query(
        query_embeddings=embedding_proyek,
        n_results=min(jumlah, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    rekomendasi = []

    for i, metadata in enumerate(hasil["metadatas"][0]):
        rekomendasi.append({
            "competition_id": metadata["competition_id"],
            "nama_lomba": metadata["name"],
            "penyelenggara": metadata["organizer"],
            "kategori": metadata["category"],
            "deskripsi": metadata["description"],
            "persyaratan": metadata["requirements"],
            "tautan_pendaftaran": metadata["registration_url"] or None,
            "sumber": metadata["source_url"] or None,
            "teks_konteks": hasil["documents"][0][i],
            "jarak": hasil["distances"][0][i],
        })

    return rekomendasi
