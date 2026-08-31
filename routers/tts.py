import uuid
import base64
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import (
    DEFAULT_VOICE_ID,
    SARVAM_API_KEY, SARVAM_BASE_URL, OUTPUT_DIR, TEST_SENTENCES,
)

router = APIRouter()


class GenerateRequest(BaseModel):
    voice_id: str = DEFAULT_VOICE_ID
    sentences: list[str] | None = None

@router.post("/generate-sarvam")
def generate_sarvam(req: GenerateRequest = GenerateRequest()):
    if not SARVAM_API_KEY:
        raise HTTPException(500, "SARVAM_API_KEY not set in .env")

    sentences = req.sentences or TEST_SENTENCES
    results = []
    url = f"{SARVAM_BASE_URL}/text-to-speech"
    headers = {"API-Subscription-Key": SARVAM_API_KEY, "Content-Type": "application/json"}

    for i, text in enumerate(sentences, start=1):
        payload = {"inputs": [text], "target_language_code": "ml-IN", "speaker": "meera", "model": "bulbul:v3"}
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            results.append({"sentence": text, "error": response.text, "status_code": response.status_code})
            continue

        audio_b64 = response.json()["audios"][0]
        audio_bytes = base64.b64decode(audio_b64)
        filename = f"sarvam_sample_{i}_{uuid.uuid4().hex[:6]}.wav"
        filepath = OUTPUT_DIR / filename
        filepath.write_bytes(audio_bytes)
        results.append({"sentence": text, "file": str(filepath)})

    return {"results": results}