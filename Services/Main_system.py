from PIL import Image
import os
from google import genai
import pandas as pd
import datetime as dt
import math
from Services.Ai_Service import generate_response
from pydantic import BaseModel, Field
import json
import re
from typing import Literal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def _user_file(prefix, username, suffix):
    if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username hanya boleh berisi 3-30 karakter: huruf, angka, atau underscore.")
    return os.path.join(PROJECT_ROOT, f"{prefix}_{username}{suffix}")

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

def Read_pengaturan(username):
    path = _user_file("Pengaturan", username, ".json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    default = {"budget_bulanan": 0, "umur": None, "berat_badan": None, "tinggi_badan": None}
    with open(path, "w") as f:
        json.dump(default, f)
    return default


def Save_pengaturan(username, budget_bulanan, umur, berat_badan, tinggi_badan):
    path = _user_file("Pengaturan", username, ".json")
    data = {
        "budget_bulanan": budget_bulanan,
        "umur": umur,
        "berat_badan": berat_badan,
        "tinggi_badan": tinggi_badan,
    }
    with open(path, "w") as f:
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
def Main_system_keuangan_(inputan_user, img, username):
    pengaturan = Read_pengaturan(username)
    konteks = bangun_konteks_kesehatan(pengaturan)

    if inputan_user == "":
        foto_struk = Image.open(img)
        contents = [foto_struk, konteks] if konteks else [foto_struk]
        response = generate_response(contents, finance_config)
    else:
        response = generate_response(inputan_user + konteks, finance_config)
    return response.parsed
    
#analisa data transaksi dari csv letak=di bawah dashboard
def Analisa_menyeluruh(username):
    df_transaksi = Read_riwayat_transaksi(username)
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
def Read_riwayat_transaksi(username):
    csv_transaksi = _user_file("Data_transaksi", username, ".csv")
    if os.path.exists(csv_transaksi):
        df = pd.read_csv(csv_transaksi)
        return df
    else:
        df_kosong = pd.DataFrame(columns=["Tanggal", "Nama", "Jumlah", "Harga", "kartegori"])
        df_kosong.to_csv(csv_transaksi, index=False, encoding="utf-8")
        return df_kosong

#Save To csv
def save_riwayat_transaksi(username, now, nama, jumlah, harga, kartegori):
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    df = Read_riwayat_transaksi(username)
    new_data = pd.DataFrame({"Tanggal": [now], "Nama": [nama], "Jumlah": [jumlah], "Harga": [harga], "kartegori": [kartegori] })
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(_user_file("Data_transaksi", username, ".csv"), index=False, encoding="utf-8")

    if kartegori == "Kesehatan":
        data_dana = Read_dana_darurat(username)
        pengurangan = float(harga) * float(jumlah)
        saldo_baru = max(float(data_dana.get("saldo", 0)) - pengurangan, 0)
        Save_dana_darurat(username, saldo_baru)


def Read_dana_darurat(username):
    path = _user_file("Dana_darurat", username, ".json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return {"saldo": max(float(data.get("saldo", 0)), 0)}
        except (OSError, ValueError, TypeError):
            pass

    default = {"saldo": 0}
    Save_dana_darurat(username, 0)
    return default


def Save_dana_darurat(username, saldo):
    path = _user_file("Dana_darurat", username, ".json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump({"saldo": max(float(saldo), 0)}, file)


def _hitung_alokasi_dana_darurat(username):
    df = Read_riwayat_transaksi(username)
    total_pengeluaran = 0.0

    if not df.empty and "Harga" in df.columns:
        try:
            total_pengeluaran = float(pd.to_numeric(df["Harga"], errors="coerce").fillna(0).sum())
        except (OSError, ValueError, TypeError):
            total_pengeluaran = 0.0

    if total_pengeluaran > 0:
        return total_pengeluaran * 0.1

    csv_kripto = os.path.join(PROJECT_ROOT, "Data_kripto.csv")
    keuntungan = 0.0

    if os.path.exists(csv_kripto):
        try:
            df_kripto = pd.read_csv(csv_kripto)
            if not df_kripto.empty:
                kolom_numerik = df_kripto.select_dtypes(include="number").columns
                if len(kolom_numerik) > 0:
                    keuntungan = float(df_kripto[kolom_numerik[0]].sum()) * 0.01
        except (OSError, ValueError, TypeError):
            keuntungan = 0.0

    return keuntungan * 0.1


def Ambil_saldo_dana_darurat(username):
    alokasi_tersedia = _hitung_alokasi_dana_darurat(username)
    saldo = Read_dana_darurat(username)["saldo"]
    df = Read_riwayat_transaksi(username)
    total_pengeluaran = 0.0

    if not df.empty and "Harga" in df.columns:
        try:
            total_pengeluaran = float(pd.to_numeric(df["Harga"], errors="coerce").fillna(0).sum())
        except (OSError, ValueError, TypeError):
            total_pengeluaran = 0.0

    return {
        "keuntungan": total_pengeluaran or (alokasi_tersedia / 0.1 if alokasi_tersedia else 0),
        "total_pengeluaran": total_pengeluaran,
        "alokasi": alokasi_tersedia,
        "terpakai": 0,
        "sisa": saldo,
        "saldo": saldo,
    }


def Alokasikan_dana_darurat(username):
    alokasi = _hitung_alokasi_dana_darurat(username)
    saldo_baru = Read_dana_darurat(username)["saldo"] + alokasi
    Save_dana_darurat(username, saldo_baru)
    return {
        "alokasi": alokasi,
        "saldo": saldo_baru,
        "sisa": saldo_baru,
    }


def Setor_manual_dana_darurat(username, jumlah):
    jumlah = float(jumlah)
    if not math.isfinite(jumlah) or jumlah <= 0:
        raise ValueError("Jumlah setor harus lebih besar dari 0.")

    data = Read_dana_darurat(username)
    saldo_baru = data.get("saldo", 0) + jumlah
    Save_dana_darurat(username, saldo_baru)
    return {"saldo": saldo_baru}


#total pengeluaran dan rata-rata pengeluaran letak=di atas dashboard dipisah menjadi 3 box
def Analisis_riwayat_transaksi(username, budget):
    df = Read_riwayat_transaksi(username)
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


from werkzeug.security import generate_password_hash, check_password_hash

USERS_PATH = os.path.join(PROJECT_ROOT, "Users.json")


def Read_users():
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, "r") as f:
            return json.load(f)
    default = {}
    with open(USERS_PATH, "w") as f:
        json.dump(default, f)
    return default


def Save_users(data):
    with open(USERS_PATH, "w") as f:
        json.dump(data, f)


def Daftar_user(username, password):
    if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
        return False, "Username hanya boleh berisi 3-30 karakter: huruf, angka, atau underscore."
    if not isinstance(password, str) or not password:
        return False, "Password wajib diisi."

    users = Read_users()
    if username in users:
        return False, "Username sudah dipakai."

    users[username] = {
        "password_hash": generate_password_hash(password)
    }
    Save_users(users)
    return True, "Berhasil daftar."


def Cek_login(username, password):
    if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
        return False

    users = Read_users()
    if username not in users:
        return False

    return check_password_hash(users[username]["password_hash"], password)

