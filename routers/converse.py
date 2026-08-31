import uuid
import base64
import asyncio
import re
import httpx
import wave
import io
from google import genai
from google.genai import types
from fastapi import APIRouter, HTTPException, UploadFile, File
from rag import retrieve_context, format_context_for_prompt
from config import SARVAM_API_KEY, SARVAM_BASE_URL, GEMINI_API_KEY, OUTPUT_DIR, SYSTEM_PROMPT
from database import classify_booking_action, save_call_event

import time

router = APIRouter()

client = genai.Client(api_key=GEMINI_API_KEY)

def merge_wav_files(audio_chunks: list[bytes]) -> bytes:
    """Merge multiple WAV byte-strings (same format) into one valid WAV file."""
    if not audio_chunks:
        return b""

    output_buffer = io.BytesIO()
    output_wav = None

    try:
        for chunk_bytes in audio_chunks:
            with wave.open(io.BytesIO(chunk_bytes), 'rb') as w:
                params = w.getparams()
                frames = w.readframes(w.getnframes())

                if output_wav is None:
                    output_wav = wave.open(output_buffer, 'wb')
                    output_wav.setparams(params)

                output_wav.writeframes(frames)
    finally:
        if output_wav is not None:
            output_wav.close()

    return output_buffer.getvalue()

@router.post("/converse-fast")
async def converse_fast(file: UploadFile = File(...)):
    if not (SARVAM_API_KEY and GEMINI_API_KEY):
        raise HTTPException(500, "SARVAM_API_KEY or GEMINI_API_KEY not set in .env")

    t0 = time.time()

    # 1. STT 
    audio_bytes = await file.read()
    async with httpx.AsyncClient(timeout=30) as http:
        stt_response = await http.post(
            f"{SARVAM_BASE_URL}/speech-to-text",
            headers={"API-Subscription-Key": SARVAM_API_KEY},
            files={"file": (file.filename, audio_bytes, file.content_type)},
            data={"model": "saarika:v2.5", "language_code": "ml-IN"},
        )
    if stt_response.status_code != 200:
        raise HTTPException(stt_response.status_code, f"STT failed: {stt_response.text}")

    transcript = stt_response.json().get("transcript", "")
    if not transcript:
        raise HTTPException(422, "Could not transcribe audio — got empty transcript")

    t1 = time.time()
    print(f"[TIMING] STT took {t1 - t0:.2f}s")
    retrieved = retrieve_context(transcript)
    context_block = format_context_for_prompt(retrieved)
    prompt = f"{context_block}\n\nCustomer said: {transcript}" if context_block else transcript


    # 2. Gemini — STREAMING
    tts_tasks = []       
    sentence_buffer = ""
    first_chunk_time = None

    async def send_to_tts(sentence: str, index: int):
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                f"{SARVAM_BASE_URL}/text-to-speech",
                headers={"API-Subscription-Key": SARVAM_API_KEY, "Content-Type": "application/json"},
                json={"inputs": [sentence], "target_language_code": "ml-IN", "speaker": "anushka", "model": "bulbul:v3"},
            )
        if resp.status_code != 200:
            return index, None
        audio_b64 = resp.json()["audios"][0]
        return index, base64.b64decode(audio_b64)

    chat = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=500,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    stream = chat.send_message_stream(prompt)

    full_reply = ""
    sentence_index = 0

    for chunk in stream:
        if not chunk.text:
            continue
        sentence_buffer += chunk.text
        full_reply += chunk.text

        # Check if we've completed a sentence
        while True:
            match = re.search(r'[.!?]\s', sentence_buffer)
            if not match:
                break
            sentence = sentence_buffer[:match.end()].strip()
            sentence_buffer = sentence_buffer[match.end():]

            if first_chunk_time is None:
                first_chunk_time = time.time()
                print(f"[TIMING] First sentence ready at {first_chunk_time - t1:.2f}s into Gemini")

            # fire off TTS for this sentence immediately, don't wait
            tts_tasks.append(asyncio.create_task(send_to_tts(sentence, sentence_index)))
            sentence_index += 1

    # any leftover text with no terminal punctuation
    if sentence_buffer.strip():
        tts_tasks.append(asyncio.create_task(send_to_tts(sentence_buffer.strip(), sentence_index)))

    t2 = time.time()
    print(f"[TIMING] Gemini full stream took {t2 - t1:.2f}s")

    # 3. Wait for all TTS tasks, then stitch audio in order
    results = await asyncio.gather(*tts_tasks)
    results.sort(key=lambda r: r[0])  # preserve sentence order
    audio_chunks = [audio for _, audio in results if audio is not None]

    combined_audio = merge_wav_files(audio_chunks)
    filepath = None
    if combined_audio:
        filename = f"converse_fast_{uuid.uuid4().hex[:6]}.wav"
        filepath = OUTPUT_DIR / filename
        filepath.write_bytes(combined_audio)

    t3 = time.time()
    print(f"[TIMING] TTS (parallel) took {t3 - t2:.2f}s")
    print(f"[TIMING] TOTAL: {t3 - t0:.2f}s")

    action = classify_booking_action(transcript)
    status = "confirmed" if action == "confirm" else "needs_followup" if action in {"cancel", "reschedule"} else "pending"
    summary = {
        "confirm": "Customer confirmed the booking.",
        "cancel": "Customer requested cancellation.",
        "reschedule": "Customer requested rescheduling.",
        "inquiry": "Customer asked a question without a clear booking decision.",
    }.get(action, "Customer interaction processed.")

    save_call_event(
        action=action,
        customer_transcript=transcript,
        agent_reply=full_reply.strip(),
        summary=summary,
        details={
            "audio_file": str(filepath) if filepath else None,
            "time_to_first_sentence": round(first_chunk_time - t1, 2) if first_chunk_time else None,
            "status": status,
        },
        status=status,
        confidence=0.8,
    )

    return {
        "you_said": transcript,
        "agent_replied": full_reply.strip(),
        "reply_audio_file": str(filepath) if filepath else None,
        "action": action,
        "status": status,
        "time_to_first_sentence": round(first_chunk_time - t1, 2) if first_chunk_time else None,
    }