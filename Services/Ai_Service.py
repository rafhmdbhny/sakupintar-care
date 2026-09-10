import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).with_name(".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY tidak ditemukan. Pastikan file .env sudah benar.")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_response(contents, config=None):
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        return response if config is not None else response.text
    except Exception as e:
        message = str(e)
        lower_message = message.lower()

        if "not_found" in lower_message or "no longer available" in lower_message or "not available to new users" in lower_message:
            raise RuntimeError(
                "Model AI yang dipilih sudah tidak tersedia lagi. Silakan update konfigurasi model ke gemini-3.6-flash."
            )
        if "UNAVAILABLE" in message or "503" in message or "temporarily unavailable" in lower_message:
            raise RuntimeError("Server AI sedang sibuk, coba beberapa saat lagi ya.")
        raise RuntimeError(f"Failed to generate response: {e}")