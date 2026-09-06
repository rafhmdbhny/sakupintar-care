from PIL import Image
import os
from google import genai
import pandas as pd
import datetime as dt
from Services.Ai_Service import generate_response
from pydantic import BaseModel, Field
import json
from typing import Literal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AnalisaMenyeluruh(BaseModel):
    kondisi_sekarang: str = Field(
        description="Analisa kondisi keuangan dan portofolio kripto user saat ini, gabungan dari data pengeluaran dan histori harga kripto yang dipantau."
    )
    proyeksi_kedepan: str = Field(
        description="Perkiraan arah ke depan kalau pola pengeluaran dan tren kripto ini berlanjut. Bukan prediksi harga pasti, tapi gambaran risiko dan peluang."
    )
    saran_aksi: list[str] = Field(
        description="Saran konkret yang bisa langsung dilakukan user, mencakup aspek keuangan sehari-hari maupun strategi kripto jangka panjang."
    )

KATEGORI_VALID = Literal[
    "Makanan & Minuman", "Transportasi", "Belanja", "Hiburan",
    "Tagihan", "Kesehatan", "Pendidikan",
    "Investasi", "Sedekah & Donasi", "Darurat/Mendadak", "Cicilan & Utang",      
    "Tabungan", "Gaya Hidup", "Pekerjaan/Bisnis", "Lainnya",
]

class HasilAnalisis(BaseModel):
    insight: str = Field(
        description="Insight atau kesimpulan utama dari data input."
    )
    kategori: list[KATEGORI_VALID] | None = Field(
        default=None,
        description=(
            "Daftar kategori/klasifikasi relevan dari 8 pilihan tetap yang tersedia. "
            "KOSONGKAN (isi array kosong [] atau null) jika input HANYA berupa pertanyaan, "
            "permintaan saran, atau jika tidak ada data yang bisa dikategorikan."
            "Kalau input berupa transaksi, isi field 'kategori' dengan urutan dari "
            "yang paling relevan ke yang paling kurang relevan — kategori pertama dalam "
            "list dianggap kategori utama transaksi tersebut."
        )
    )
    rekomendasi_aksi: list[str] = Field(
        description="Langkah konkret, jawaban, atau rekomendasi solusi berdasarkan input."
    )
    nama_transaksi: str | None = Field(
        default=None,
        description="Nama barang/transaksi yang disebut user. KOSONGKAN jika input bukan transaksi."
    )
    harga: int | None = Field(
        default=None,
        description="Harga dalam Rupiah jika disebutkan user. KOSONGKAN (null) jika tidak disebutkan/tidak diketahui."
    )

AnalisaMenyeluruh_config = genai.types.GenerateContentConfig(
    system_instruction="Kamu adalah Analis Kripto dan Penasihat Finansial yang objektif, bijak, dan berbasis data. Tugasmu adalah menganalisis pasar kripto secara rasional dengan manajemen risiko tinggi, mengevaluasi pengeluaran pribadi serta penganggaran, dan memberikan saran keuangan yang disesuaikan dengan profil risiko pengguna. Sampaikan jawaban secara langsung, terstruktur, tanpa kalimat bertele-tele, dan selalu sertakan pengingat edukatif bahwa analisis ini bukan nasihat keuangan resmi (DYOR)",
    temperature=0.3,
    response_mime_type="application/json",   # 1. cek: bukan "response_mine_type"
    response_schema=AnalisaMenyeluruh,         # 2. cek: nunjuk ke CLASS BaseModel yang bener
)

finance_config = genai.types.GenerateContentConfig(
    system_instruction="Kamu adalah asisten keuangan galak yang selalu mengingatkan user untuk hemat. " \
                       "Jelaskan penjelasan berdasarkan data dari user dan berikan saran yang sesuai. " \
                       "Jangan memberikan saran yang tidak relevan.",
    temperature=0.3,
    response_schema=HasilAnalisis,
    response_mime_type="application/json",
)

PENGATURAN_PATH = os.path.join(PROJECT_ROOT, "Pengaturan.json")

def Read_pengaturan():
    if os.path.exists(PENGATURAN_PATH):
        with open(PENGATURAN_PATH, "r") as f:
            return json.load(f)
    default = {"budget_bulanan": 0, "umur": None, "berat_badan": None, "tinggi_badan": None}
    with open(PENGATURAN_PATH, "w") as f:
        json.dump(default, f)
    return default


def Save_pengaturan(budget_bulanan, umur, berat_badan, tinggi_badan):
    data = {
        "budget_bulanan": budget_bulanan,
        "umur": umur,
        "berat_badan": berat_badan,
        "tinggi_badan": tinggi_badan,
    }
    with open(PENGATURAN_PATH, "w") as f:
        json.dump(data, f)


def bangun_konteks_kesehatan(pengaturan):
    umur = pengaturan.get("umur")
    bb = pengaturan.get("berat_badan")
    tinggi = pengaturan.get("tinggi_badan")

    if not (umur and bb and tinggi):
        return ""  # data belum lengkap, jangan ikut prompt

    bmi = bb / ((tinggi / 100) ** 2)
    return (
        f"\n\nKonteks tambahan tentang user: umur {umur} tahun, berat badan {bb} kg, "
        f"tinggi badan {tinggi} cm (BMI sekitar {bmi:.1f}). Pertimbangkan aspek kesehatan "
        "ini kalau relevan dengan pertanyaan/analisis keuangan user, misal soal pola "
        "belanja makanan atau gaya hidup."
    )

#Sistem keuangan utama letak=di atas dashboard
def Main_system_keuangan_(inputan_user, img):
    pengaturan = Read_pengaturan()
    konteks = bangun_konteks_kesehatan(pengaturan)

    if inputan_user == "":
        foto_struk = Image.open(img)
        # kalau ada foto, konteks teks digabung sebagai elemen terpisah dalam list
        contents = [foto_struk, konteks] if konteks else [foto_struk]
        response = generate_response(contents, finance_config)
    else:
        response = generate_response(inputan_user + konteks, finance_config)
    return response.parsed
    
#analisa data transaksi dari csv letak=di bawah dashboard
def Analisa_menyeluruh():
    df_transaksi = Read_riwayat_transaksi()
    csv_kripto = os.path.join(PROJECT_ROOT, "Data_kripto.csv")
    df_kripto = pd.read_csv(csv_kripto) if os.path.exists(csv_kripto) else pd.DataFrame()

    if df_transaksi.empty and df_kripto.empty:
        return None

    contents = f"""
    Berikut data pengeluaran user:
    {df_transaksi.to_string(index=False) if not df_transaksi.empty else "Belum ada data pengeluaran."}

    Berikut histori harga kripto yang dipantau user:
    {df_kripto.to_string(index=False) if not df_kripto.empty else "Belum ada data kripto."}

    Analisa kondisi keuangan dan kripto user secara menyeluruh:
    1. Bagaimana kondisi sekarang (pengeluaran + portofolio kripto)?
    2. Bagaimana proyeksi ke depan kalau pola ini berlanjut?
    3. Apa saran konkret yang bisa dilakukan?
    """

    response = generate_response(contents, AnalisaMenyeluruh_config)
    return response.parsed


#Read csv
def Read_riwayat_transaksi():
    csv_transaksi = os.path.join(PROJECT_ROOT, "Data_transaksi.csv")
    if os.path.exists(csv_transaksi):
        df = pd.read_csv(csv_transaksi)
        return df
    else:
        df_kosong = pd.DataFrame(columns=["Tanggal", "Nama", "Jumlah", "Harga", "kartegori"])
        df_kosong.to_csv(csv_transaksi, index=False, encoding="utf-8")
        return df_kosong

#Save To csv
def save_riwayat_transaksi(now, nama, jumlah, harga, kartegori):
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    df = Read_riwayat_transaksi()
    new_data = pd.DataFrame({"Tanggal": [now], "Nama": [nama], "Jumlah": [jumlah], "Harga": [harga], "kartegori": [kartegori] })
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(os.path.join(PROJECT_ROOT, "Data_transaksi.csv"), index=False, encoding="utf-8")


#total pengeluaran dan rata-rata pengeluaran letak=di atas dashboard dipisah menjadi 3 box
def Analisis_riwayat_transaksi(budget):
    df = Read_riwayat_transaksi()
    if df.empty:
        return 0, 0, 0
    total_pengeluaran = float(df['Harga'].sum())
    rata_rata_pengeluaran = float(df['Harga'].mean())
    persenan_pengeluaran = (total_pengeluaran / budget * 100) if budget > 0 else 0
    return total_pengeluaran, rata_rata_pengeluaran, persenan_pengeluaran


class HasilKesehatan(BaseModel):
    insight: str = Field(
        description="Ringkasan kondisi kesehatan user berdasarkan BMI, umur, dan keluhan yang disebutkan."
    )
    kategori: list[str] = Field(
        description=(
            "Status/kategori kesehatan yang relevan, misal status BMI "
            "(Kurus/Normal/Gemuk/Obesitas) dan tanda risiko lain kalau ada."
        )
    )
    rekomendasi_aksi: list[str] = Field(
        description="Saran konkret gaya hidup sehat yang bisa langsung dilakukan user (pola makan, olahraga, istirahat, dll)."
    )
    perlu_konsultasi_dokter: bool = Field(
        default=False,
        description="True kalau keluhan user menunjukkan tanda yang sebaiknya diperiksakan ke tenaga medis."
    )


kesehatan_config = genai.types.GenerateContentConfig(
    system_instruction=(
        "Kamu adalah asisten kesehatan yang suportif tapi tegas, mendorong gaya hidup sehat "
        "berbasis data BMI, umur, dan keluhan user. Berikan saran praktis dan mudah diikuti. "
        "Jangan mendiagnosis penyakit tertentu — kalau keluhan terdengar serius, sarankan "
        "konsultasi ke tenaga medis profesional."
    ),
    temperature=0.3,
    response_schema=HasilKesehatan,
    response_mime_type="application/json",
)


def Analisa_kesehatan(umur, berat, tinggi, bmi, kategori_bmi, keluhan):
    contents = f"""
    Data kesehatan user:
    Umur: {umur if umur else "tidak diisi"} tahun
    Berat badan: {berat} kg
    Tinggi badan: {tinggi} cm
    BMI: {bmi} ({kategori_bmi})
    Keluhan: {keluhan if keluhan else "tidak ada keluhan yang disebutkan"}

    Berikan analisis kondisi kesehatan singkat dan saran aksi gaya hidup yang relevan.
    """
    response = generate_response(contents, kesehatan_config)
    return response.parsed

