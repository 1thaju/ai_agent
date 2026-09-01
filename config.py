import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_BASE_URL = "https://api.sarvam.ai"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OUTPUT_DIR = Path("output_audio")
OUTPUT_DIR.mkdir(exist_ok=True)

TEST_SENTENCES = [
    "നമസ്കാരം, ഞാൻ നിങ്ങളുടെ ബുക്കിംഗ് കൺഫേം ചെയ്യാൻ വിളിക്കുകയാണ്.",
    "നിങ്ങളുടെ അപ്പോയിന്റ്മെന്റ് നാളെ ഉച്ചയ്ക്ക് 3 മണിക്കാണ്.",
    "ദയവായി 10 മിനിറ്റ് മുൻപ് എത്തിച്ചേരുക.",
    "ഇത് ക്യാൻസൽ ചെയ്യണോ അതോ റീഷെഡ്യൂൾ ചെയ്യണോ?",
    "നന്ദി, നല്ല ദിവസം ആശംസിക്കുന്നു."
]

SYSTEM_PROMPT = """You are a polite booking confirmation assistant calling on behalf of a business in Kerala.
Always reply in natural, conversational Malayalam only — no English, no transliteration.
Keep replies short (1-2 sentences), like a real phone call, not a written message.
Your job: confirm appointment/booking details, answer simple questions about date/time, and politely close the call.
If the customer wants to cancel or reschedule, acknowledge it and say a human will follow up.
."""