
import requests
from fastapi import  APIRouter, HTTPException , File, UploadFile

from config import SARVAM_API_KEY, SARVAM_BASE_URL

router = APIRouter()
 
@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language_code: str = "ml-IN"):
    if not SARVAM_API_KEY:
        raise HTTPException(500, "SARVAM_API_KEY not set in .env")

    url = f"{SARVAM_BASE_URL}/speech-to-text"
    headers = {"API-Subscription-Key": SARVAM_API_KEY}

    audio_bytes = await file.read()
    files = {
        "file": (file.filename, audio_bytes, file.content_type),
    }
    data = {
        "model": "saarika:v2.5",
        "language_code": language_code,
    }

    response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code != 200:
        raise HTTPException(response.status_code, response.text)

    return response.json()