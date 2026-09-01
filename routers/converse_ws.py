import asyncio
import base64
import re
import time

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai import types

from config import SARVAM_API_KEY, SARVAM_BASE_URL, SYSTEM_PROMPT
from rag import retrieve_context, format_context_for_prompt
from database import classify_booking_action, save_call_event


from routers.converse import client, merge_wav_files

router = APIRouter()


@router.websocket("/ws/converse")
async def ws_converse(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")

    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            print(f"[WS] Received {len(audio_bytes)} bytes of audio")

            t0 = time.time()

            # 1. STT
            async with httpx.AsyncClient(timeout=30) as http:
                stt_response = await http.post(
                    f"{SARVAM_BASE_URL}/speech-to-text",
                    headers={"API-Subscription-Key": SARVAM_API_KEY},
                    files={"file": ("audio.webm", audio_bytes, "audio/webm")},
                    data={"model": "saarika:v2.5", "language_code": "ml-IN"},
                )
            if stt_response.status_code != 200:
                await websocket.send_json({"type": "error", "message": f"STT failed: {stt_response.text}"})
                continue

            transcript = stt_response.json().get("transcript", "")
            if not transcript:
                await websocket.send_json({"type": "error", "message": "Could not transcribe — empty transcript"})
                continue

            t1 = time.time()
            print(f"[WS TIMING] STT took {t1 - t0:.2f}s")

            await websocket.send_json({"type": "transcript", "text": transcript})

            # 2. RAG
            retrieved = retrieve_context(transcript)
            context_block = format_context_for_prompt(retrieved)
            prompt = f"{context_block}\n\nCustomer said: {transcript}" if context_block else transcript

            # 3. Gemini streaming + sentence-by-sentence TTS
            tts_tasks = []
            sentence_buffer = ""
            sentence_index = 0
            full_reply = ""

            async def send_to_tts(sentence: str, index: int):
                async with httpx.AsyncClient(timeout=30) as http:
                    resp = await http.post(
                        f"{SARVAM_BASE_URL}/text-to-speech",
                        headers={"API-Subscription-Key": SARVAM_API_KEY, "Content-Type": "application/json"},
                        json={"inputs": [sentence], "target_language_code": "ml-IN", "speaker": "ritu", "model": "bulbul:v3"},
                    )
                if resp.status_code != 200:
                    print(f"[ERROR] TTS failed for sentence {index}: {resp.status_code} — {resp.text}")
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
            chat = client.chats.create(
                model="gemini-3.6-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=500,
                    thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                ),
            )

            def run_gemini_stream():
                """Blocking call — runs in a separate thread so it doesn't freeze the event loop."""
                return list(chat.send_message_stream(prompt))

            chunks = await asyncio.to_thread(run_gemini_stream)

            for chunk in chunks:
                if not chunk.text:
                    continue
                sentence_buffer += chunk.text
                full_reply += chunk.text

                while True:
                    match = re.search(r'[.!?]\s', sentence_buffer)
                    if not match:
                        break
                    sentence = sentence_buffer[:match.end()].strip()
                    sentence_buffer = sentence_buffer[match.end():]
                    tts_tasks.append(asyncio.create_task(send_to_tts(sentence, sentence_index)))
                    sentence_index += 1
            if sentence_buffer.strip():
                tts_tasks.append(asyncio.create_task(send_to_tts(sentence_buffer.strip(), sentence_index)))

            t2 = time.time()
            print(f"[WS TIMING] Gemini took {t2 - t1:.2f}s")

            await websocket.send_json({"type": "reply_text", "text": full_reply.strip()})

            # 4. Merge audio, send back as raw bytes
            results = await asyncio.gather(*tts_tasks)
            results.sort(key=lambda r: r[0])
            audio_chunks = [audio for _, audio in results if audio is not None]
            combined_audio = merge_wav_files(audio_chunks)

            t3 = time.time()
            print(f"[WS TIMING] TTS took {t3 - t2:.2f}s | TOTAL: {t3 - t0:.2f}s")

            if combined_audio:
                await websocket.send_bytes(combined_audio)
            else:
                await websocket.send_json({"type": "error", "message": "TTS produced no audio"})

            # 5. Classify + persist
            action = classify_booking_action(transcript)
            status = (
                "confirmed" if action == "confirm"
                else "needs_followup" if action in {"cancel", "reschedule"}
                else "pending"
            )
            save_call_event(
                action=action,
                customer_transcript=transcript,
                agent_reply=full_reply.strip(),
                summary="",
                details={"channel": "websocket", "total_time": round(t3 - t0, 2)},
                status=status,
                confidence=0.8,
            )

    except WebSocketDisconnect:
        print("[WS] Client disconnected")