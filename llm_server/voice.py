from __future__ import annotations

import base64
from typing import Any, Dict, Optional


def transcribe(audio_base64: Optional[str] = None, url: Optional[str] = None, language: Optional[str] = None) -> Dict[str, Any]:
    # Stub transcription; real ASR backend can be wired later (e.g., Whisper cpp/server)
    return {
        "text": "",  # empty until ASR is available
        "segments": [],
        "language": language or "auto",
        "note": "ASR stub: install real backend to enable transcription",
    }


def tts(text: str, voice: Optional[str] = None, format: str = "mp3") -> Dict[str, Any]:
    # Stub TTS: returns a tiny silent payload marker
    payload = base64.b64encode(b"stub-audio").decode("ascii")
    return {
        "audio": payload,
        "format": format,
        "voice": voice or "default",
        "note": "TTS stub: install real backend to enable synthesis",
    }

