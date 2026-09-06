from google import genai
from pydantic import BaseModel, Field

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
