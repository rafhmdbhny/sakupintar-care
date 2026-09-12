from google import genai
from pydantic import BaseModel, Field
from typing import Literal
import os
import datetime as dt
import pandas as pd

from Services.Ai_Service import generate_response


class HasilAnalisaKesehatan(BaseModel):
    saran: str = Field(
        description="Saran kesehatan umum yang aman berdasarkan data pengguna."
    )


health_config = genai.types.GenerateContentConfig(
    system_instruction=(
        "Kamu adalah asisten kesehatan umum. Berikan saran singkat, praktis, "
        "dan mudah dipahami berdasarkan umur, berat badan, tinggi badan, BMI, "
        "serta keluhan pengguna. Jangan mendiagnosis atau menggantikan dokter. "
        "Jika ada tanda bahaya atau keluhan berat, sarankan segera mencari "
        "pertolongan medis. Sertakan pengingat bahwa ini bukan diagnosis medis."
    ),
    temperature=0.3,
    response_mime_type="application/json",
    response_schema=HasilAnalisaKesehatan,
)


def Analisa_kesehatan(umur, berat, tinggi, bmi, kategori_bmi, keluhan):
    if berat is None or tinggi is None or bmi is None:
        raise ValueError("Data berat, tinggi, dan BMI wajib diisi.")

    contents = (
        "Analisa kesehatan umum pengguna berikut:\n"
        f"Umur: {umur or 'Tidak diisi'} tahun\n"
        f"Berat badan: {berat} kg\n"
        f"Tinggi badan: {tinggi} cm\n"
        f"BMI: {bmi}\n"
        f"Kategori BMI: {kategori_bmi or 'Tidak diisi'}\n"
        f"Keluhan: {keluhan or 'Tidak ada keluhan'}"
    )

    response = generate_response(contents, health_config)
    return response.parsed


# ===========================================================================
# KONSUMSI & AKTIVITAS (BARU)
# ===========================================================================

KATEGORI_SEHAT = Literal["Sehat", "Kurang Sehat", "Tidak Sehat"]


class AnalisaNutrisi(BaseModel):
    nama: str = Field(description="Nama makanan/minuman yang dikonsumsi, atau nama aktivitas fisik.")
    jenis: Literal["Konsumsi", "Aktivitas"] = Field(
        description="'Konsumsi' jika ini makanan/minuman, 'Aktivitas' jika ini aktivitas fisik/olahraga."
    )
    kalori: int = Field(
        description=(
            "Perkiraan kalori. Untuk Konsumsi: kalori yang MASUK ke tubuh. "
            "Untuk Aktivitas: perkiraan kalori yang TERBAKAR. Selalu isi angka "
            "perkiraan terbaik walau user tidak menyebutkan detail porsi/durasi."
        )
    )
    catatan_nutrisi: str = Field(
        description=(
            "Untuk Konsumsi: ringkasan kandungan gizi utama (karbohidrat, protein, "
            "lemak, gula, serat, dll yang relevan). Untuk Aktivitas: ringkasan "
            "intensitas dan manfaatnya."
        )
    )
    kategori_kesehatan: KATEGORI_SEHAT = Field(
        description=(
            "Kategori dampak kesehatan dari entri ini: 'Sehat', 'Kurang Sehat', "
            "atau 'Tidak Sehat'. Untuk konsumsi, pertimbangkan kalori berlebih, "
            "gula/lemak jenuh tinggi, dll. Untuk aktivitas, 'Sehat' untuk gerak "
            "fisik yang bermanfaat, 'Kurang Sehat' jika terlalu ringan/singkat."
        )
    )
    alasan: str = Field(description="Alasan singkat kenapa dikategorikan begitu.")


nutrisi_config = genai.types.GenerateContentConfig(
    system_instruction=(
        "Kamu adalah asisten gizi dan aktivitas fisik. User akan menyebutkan "
        "makanan/minuman yang dikonsumsi ATAU aktivitas fisik yang dilakukan "
        "dalam satu kalimat bebas. Identifikasi jenisnya (Konsumsi/Aktivitas), "
        "perkirakan kalori dan kandungan gizi/intensitasnya, lalu kategorikan "
        "dampak kesehatannya. Selalu beri estimasi angka kalori walau data user "
        "minim/gak detail — pakai pengetahuan gizi umum buat nebak porsi wajar. "
        "Ini bukan pengganti ahli gizi profesional."
    ),
    temperature=0.3,
    response_mime_type="application/json",
    response_schema=AnalisaNutrisi,
)


def _path_konsumsi(username):
    return f"Data_konsumsi_{username}.csv"


def Catat_konsumsi(username, deskripsi):
    contents = f"Catat entri berikut: {deskripsi}"
    response = generate_response(contents, nutrisi_config)
    hasil = response.parsed

    path = _path_konsumsi(username)
    baris_baru = pd.DataFrame({
        "Tanggal": [dt.datetime.now().strftime("%Y-%m-%d %H:%M")],
        "Jenis": [hasil.jenis],
        "Nama": [hasil.nama],
        "Kalori": [hasil.kalori],
        "Catatan_Nutrisi": [hasil.catatan_nutrisi],
        "Kategori": [hasil.kategori_kesehatan],
        "Alasan": [hasil.alasan],
    })

    if os.path.exists(path):
        df_lama = pd.read_csv(path)
        df_baru = pd.concat([df_lama, baris_baru], ignore_index=True)
    else:
        df_baru = baris_baru

    df_baru.to_csv(path, index=False, encoding="utf-8")
    return hasil


def Baca_riwayat_konsumsi(username):
    path = _path_konsumsi(username)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=["Tanggal", "Jenis", "Nama", "Kalori", "Catatan_Nutrisi", "Kategori", "Alasan"])


class AnalisaKesehatanMenyeluruh(BaseModel):
    kondisi_sekarang: str = Field(description="Gambaran pola konsumsi & aktivitas pengguna saat ini.")
    proyeksi_kedepan: str = Field(description="Perkiraan dampak ke depan kalau pola ini berlanjut.")
    saran_aksi: list[str] = Field(description="Saran aksi konkret buat perbaiki/pertahanin pola sehat.")


kesehatan_menyeluruh_config = genai.types.GenerateContentConfig(
    system_instruction=(
        "Kamu adalah asisten kesehatan yang menganalisa pola konsumsi makanan/minuman "
        "dan aktivitas fisik pengguna dari waktu ke waktu berdasarkan data historis "
        "yang diberikan. Berikan gambaran kondisi sekarang, proyeksi kalau pola ini "
        "berlanjut, dan saran aksi konkret. Ini BUKAN diagnosis medis — selalu "
        "ingatkan buat konsultasi ke ahli gizi/dokter untuk keluhan serius."
    ),
    temperature=0.3,
    response_mime_type="application/json",
    response_schema=AnalisaKesehatanMenyeluruh,
)


def Analisa_kesehatan_menyeluruh(username):
    df = Baca_riwayat_konsumsi(username)
    if df.empty:
        return None

    contents = (
        "Berikut riwayat konsumsi & aktivitas pengguna:\n"
        f"{df.to_string(index=False)}\n\n"
        "Analisa pola ini secara menyeluruh."
    )

    response = generate_response(contents, kesehatan_menyeluruh_config)
    return response.parsed
