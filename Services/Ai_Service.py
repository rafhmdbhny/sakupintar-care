import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).with_name(".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY tidak ditemukan. Pastikan file .env sudah benar.")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_response(contents, config=None):
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=config,
        )
        return response if config is not None else response.text
    except Exception as e:
        raise RuntimeError(f"Failed to generate response: {e}")