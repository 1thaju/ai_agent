import os
import uuid
from pathlib import Path
 
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
 
load_dotenv()
 
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_BASE_URL = "https://api.sarvam.ai"

DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
 
OUTPUT_DIR = Path("output_audio")
OUTPUT_DIR.mkdir(exist_ok=True)
 
TEST_SENTENCES = [
    "നമസ്കാരം, ഞാൻ നിങ്ങളുടെ ബുക്കിംഗ് കൺഫേം ചെയ്യാൻ വിളിക്കുകയാണ്.",
    "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് നാളെ ഉച്ചയ്ക്ക് 3 മണിക്കാണ്.",
    "ദയവായി 10 മിനിറ്റ് മുൻപ് എത്തിച്ചേരുക.",
    "ഇത് ക്യാൻസൽ ചെയ്യണോ അതോ റീഷെഡ്യൂൾ ചെയ്യണോ?",
    "നന്ദി, നല്ല ദിവസം ആശംസിക്കുന്നു."
]
 
 
class GenerateRequest(BaseModel):
    voice_id: str = DEFAULT_VOICE_ID
    sentences: list[str] | None = None  
 
 
app = FastAPI(title="Malayalam Calling Agent — TTS Test")
 
 
@app.get("/")
def root():
    return {
        "status": "ok",
        "note": "POST /generate to create Malayalam TTS samples from ElevenLabs",
        "sentences_loaded": len(TEST_SENTENCES),
    }
 
 
# @app.post("/generate")
# def generate(req: GenerateRequest = GenerateRequest()):
#     if not SARVAM_API_KEY:
#         raise HTTPException(500, "SARVAM_API_KEY not set in .env")
 
#     sentences = req.sentences or TEST_SENTENCES
#     results = []
 
#     for i, text in enumerate(sentences, start=1):
#         url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{req.voice_id}"
#         headers = {
#             "xi-api-key": SARVAM_API_KEY,
#             "Content-Type": "application/json",
#         }
#         payload = {
#             "text": text,
#             "model_id": "eleven_multilingual_v2",
#             "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
#         }
 
#         response = requests.post(url, json=payload, headers=headers)
 
#         if response.status_code != 200:
#             results.append(
#                 {
#                     "sentence": text,
#                     "error": response.text,
#                     "status_code": response.status_code,
#                 }
#             )
#             continue
 
#         filename = f"sample_{i}_{uuid.uuid4().hex[:6]}.mp3"
#         filepath = OUTPUT_DIR / filename
#         filepath.write_bytes(response.content)
 
#         results.append({"sentence": text, "file": str(filepath)})
 
#     return {"results": results}

@app.post("/generate-sarvam")
def generate_sarvam(req: GenerateRequest = GenerateRequest()):
    if not SARVAM_API_KEY:
        raise HTTPException(500, "SARVAM_API_KEY not set in .env")

    sentences = req.sentences or TEST_SENTENCES
    results = []

    url = f"{SARVAM_BASE_URL}/text-to-speech"
    headers = {
        "API-Subscription-Key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    for i, text in enumerate(sentences, start=1):
        payload = {
            "inputs": [text],
            "target_language_code": "ml-IN",
            "speaker": "manisha",
            "model": "bulbul:v2",
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            results.append(
                {"sentence": text, "error": response.text, "status_code": response.status_code}
            )
            continue

        # Sarvam returns base64-encoded audio inside JSON
        import base64
        audio_b64 = response.json()["audios"][0]
        audio_bytes = base64.b64decode(audio_b64)

        filename = f"sarvam_sample_{i}_{uuid.uuid4().hex[:6]}.wav"
        filepath = OUTPUT_DIR / filename
        filepath.write_bytes(audio_bytes)

        results.append({"sentence": text, "file": str(filepath)})

    return {"results": results}
# @app.get("/voices")
# def list_voices():
#     if not ELEVENLABS_API_KEY:
#         raise HTTPException(500, "ELEVENLABS_API_KEY not set in .env")

#     url = f"{ELEVENLABS_BASE_URL}/voices"
#     headers = {"xi-api-key": ELEVENLABS_API_KEY}
#     response = requests.get(url, headers=headers)

#     if response.status_code != 200:
#         raise HTTPException(response.status_code, response.text)

#     data = response.json()
#     return [
#         {"name": v["name"], "voice_id": v["voice_id"], "category": v.get("category")}
#         for v in data.get("voices", [])
#     ]
 
@app.get("/audio/{filename}")
def get_audio(filename: str):
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(filepath, media_type="audio/mpeg")
 
 
