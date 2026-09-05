import os
import datetime as dt
import requests
import pandas as pd
from google import genai
from pydantic import BaseModel, Field

from Services.Ai_Service import generate_response

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_KRIPTO = os.path.join(PROJECT_ROOT, "Data_kripto.csv")


class AnalisaInvestasiKripto(BaseModel):
    ringkasan_tren: str = Field(
        description="Ringkasan pergerakan harga dalam konteks jangka panjang, bukan fluktuasi harian."
    )
    tingkat_risiko: str = Field(
        description="Tinggi, Sedang, atau Rendah — dari sudut pandang investor jangka panjang."
    )
    cocok_untuk_hold: str = Field(
        description=(
            "Penilaian singkat soal kesesuaian aset ini untuk dipegang jangka panjang "
            "(misal: 'volatilitas tinggi, cocok untuk yang toleransi risikonya besar', dll). "
            "JANGAN berbentuk sinyal beli/jual."
        )
    )
    rekomendasi: list[str] = Field(
        description=(
            "Saran strategi jangka panjang (contoh: diversifikasi portofolio, DCA/dollar-cost "
            "averaging, alokasi proporsi aset, riset fundamental proyek). "
            "JANGAN berisi ajakan 'beli sekarang' atau 'jual sekarang'."
        )
    )


kripto_config = genai.types.GenerateContentConfig(
    system_instruction=(
        "Kamu adalah asisten edukasi investasi kripto untuk investor jangka panjang "
        "(long-term holder), BUKAN untuk day trader. "
        "Fokus jawabanmu pada gambaran tren besar, tingkat risiko, dan strategi "
        "jangka panjang seperti dollar-cost averaging dan diversifikasi. "
        "JANGAN PERNAH memberikan sinyal beli/jual jangka pendek, target harga, "
        "atau ajakan trading. Selalu ingatkan bahwa kripto sangat fluktuatif dan "
        "ini bukan nasihat finansial."
    ),
    temperature=0.3,
    response_mime_type="application/json",
    response_schema=AnalisaInvestasiKripto,
)


def Ambil_dan_simpan_harga(koin="bitcoin"):
    res = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": koin, "vs_currencies": "idr", "include_24hr_change": "true"},
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()[koin]

    baris_baru = pd.DataFrame({
        "Waktu": [dt.datetime.now().strftime("%Y-%m-%d %H:%M")],
        "Koin": [koin],
        "Harga_IDR": [data["idr"]],
        "Perubahan_24jam": [data.get("idr_24h_change", 0)],
    })

    if os.path.exists(CSV_KRIPTO):
        df_lama = pd.read_csv(CSV_KRIPTO)
        df_baru = pd.concat([df_lama, baris_baru], ignore_index=True)
    else:
        df_baru = baris_baru

    df_baru.to_csv(CSV_KRIPTO, index=False, encoding="utf-8")
    return data

def Analisa_kripto(koin):
    if not os.path.exists(CSV_KRIPTO):
        return None

    df = pd.read_csv(CSV_KRIPTO)
    df_koin = df[df["Koin"] == koin]   

    if df_koin.empty:
        return None

    contents = f"""
    Berikut histori harga {koin} yang tercatat (dalam Rupiah):
    {df_koin.to_string(index=False)}

    Analisa ini dari sudut pandang investor jangka panjang (bukan trader harian).
    Fokus ke tren besar, tingkat risiko, dan strategi jangka panjang untuk koin ini.
    """

    response = generate_response(contents, kripto_config)
    return response.parsed