# Malayalam Calling Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Voice-AI-FF6B6B?style=for-the-badge" alt="Voice AI" />
  <img src="https://img.shields.io/badge/Malayalam-Enabled-0A84FF?style=for-the-badge" alt="Malayalam enabled" />
</p>

A production-style voice assistant for Malayalam customer conversations. This app listens to incoming audio, transcribes it with Sarvam AI, matches the user intent against a local knowledge base, generates a natural Malayalam reply with Gemini, and speaks it back using Sarvam TTS.

It is designed for booking, inquiry, cancellation, and rescheduling flows in a hospitality or service-business setting.

## Demo flow

```text
Mic / Audio Input
   ↓
Speech-to-Text (Sarvam)
   ↓
Knowledge Retrieval (local KB)
   ↓
Gemini Response Generation
   ↓
Text-to-Speech (Sarvam)
   ↓
Audio Playback + Call Logging
```

## Highlights

- Real-time WebSocket voice conversation flow
- Malayalam-first system prompt and conversational output
- Local business knowledge matching through `knowledge_base.json`
- Booking intent classification for confirm / cancel / reschedule / inquiry
- SQLite-backed call tracking and state persistence
- Minimal browser testing harness with `ws_test.html`
- FastAPI endpoints for both upload-based and streaming usage

## Tech stack

- Python
- FastAPI
- SQLite
- Google GenAI SDK
- Sarvam AI STT/TTS APIs
- HTTPX

## Project structure

```text
call-agent/
├── main.py                  # FastAPI app and router registration
├── config.py                # environment variables and shared config
├── database.py              # SQLite schema and call-event persistence
├── rag.py                   # lightweight RAG / keyword matching logic
├── knowledge_base.json      # business context for customer replies
├── requirements.txt         # Python dependencies
├── ws_test.html             # browser-based audio test client
├── test_converse.py         # basic regression/unit test
├── output_audio/            # generated audio files
├── bookings.db              # auto-created local SQLite DB
├── routers/
│   ├── converse.py          # upload-based voice conversation
│   ├── converse_ws.py       # WebSocket-driven live conversation
│   ├── stt.py               # Sarvam STT endpoint
│   └── tts.py               # TTS sample generation endpoint
├── .env                     # local API keys (not committed)
└── README.md                # project documentation
```

## Getting started

### 1) Clone the repo

```bash
git clone <your-repo-url>
cd call-agent
```

### 2) Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Add your environment variables

Create a `.env` file in the project root:

```env
SARVAM_API_KEY=your_sarvam_api_key
GEMINI_API_KEY=your_google_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### 5) Run the API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

## API overview

### Core endpoints

- `GET /` — health check
- `POST /converse-fast` — upload a voice clip and get a full response
- `POST /transcribe` — transcribe audio with Sarvam STT
- `POST /generate-sarvam` — generate sample TTS output
- `WS /ws/converse` — live streaming voice conversation

### Example response from `POST /converse-fast`

```json
{
  "you_said": "പൊന്നാനി യാത്രക്കായി ബുക്ക് ചെയ്യണം",
  "agent_replied": "താങ്കളുടെ ബുക്കിംഗ് സ്ഥിരീകരിച്ചിരിക്കുന്നു.",
  "reply_audio_file": "output_audio/converse_fast_abc123.wav",
  "action": "confirm",
  "status": "confirmed"
}
```

## WebSocket conversation flow

1. Browser or client sends recorded audio over WebSocket.
2. Server uploads the audio to Sarvam STT.
3. Transcript is matched against `knowledge_base.json` for relevant business info.
4. Gemini builds the human-like Malayalam response.
5. The response is split into sentences and converted to speech.
6. Audio chunks are merged and sent back to the client.
7. The outcome is stored in SQLite as a call event.

## Browser testing

Open the file [ws_test.html](ws_test.html) in a browser to test the live call flow.

It:

- connects to `ws://127.0.0.1:8000/ws/converse`
- captures microphone input
- sends recorded audio to the backend
- prints the transcript and final reply
- plays the returned audio response

## Data and outputs

The app creates and uses:

- `bookings.db` for event logging and booking state
- `output_audio/` for generated WAV files

## Why this project matters

This project demonstrates a practical AI calling workflow for local businesses:

- voice interaction without a custom telecom stack
- multilingual support for Malayalam
- quick integration with business knowledge and appointment workflows
- a small, self-contained backend suitable for demos and internal automation

## Run tests

```bash
python -m unittest
```

## License

This project is intended for local development and business experimentation. If you plan to publish or deploy it externally, add a license that matches your distribution requirements.
