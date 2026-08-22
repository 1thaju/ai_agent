from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from config import OUTPUT_DIR
from routers import tts, stt, converse

app = FastAPI(title="Malayalam Calling Agent")

app.include_router(tts.router)
app.include_router(stt.router)
app.include_router(converse.router)


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/audio/{filename}")
def get_audio(filename: str):
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(filepath, media_type="audio/mpeg")