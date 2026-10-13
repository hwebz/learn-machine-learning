from __future__ import annotations

import io
from typing import Any
import structlog
from openai import AsyncOpenAI

from app.adapters.capabilities.base import IVoiceTranscriber
from app.core.config import settings

logger = structlog.get_logger(__name__)


class VoiceTranscriberService:
    """Asynchronous voice-to-text service implementing IVoiceTranscriber.

    Streams or transmits audio data to an OpenAI-compatible Whisper STT endpoint
    or provides a clean fallback.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = base_url or settings.router_base_url
        self.api_key = api_key or settings.router_api_key

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice_input.webm", content_type: str = "audio/webm") -> str:
        """Asynchronously send audio file bytes to the configured STT backend."""
        if not audio_bytes:
            raise ValueError("No audio content provided for transcription.")

        logger.info("voice_transcription_requested", bytes_len=len(audio_bytes), filename=filename, content_type=content_type)

        # 1. Attempt OpenAI-compatible Whisper transcription via configured router / API
        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key, timeout=30.0)
        try:
            # File tuple accepted by OpenAI SDK: (filename, file_bytes, content_type)
            file_tuple = (filename, audio_bytes, content_type)
            result = await client.audio.transcriptions.create(
                model="whisper-1",
                file=file_tuple,  # type: ignore[arg-type]
            )
            transcription = (result.text or "").strip()
            if transcription:
                logger.info("voice_transcription_success", length=len(transcription))
                return transcription
        except Exception as exc:
            logger.warning("router_whisper_transcription_failed", error=str(exc))
        finally:
            await client.close()

        # 2. If the router failed or is not running Whisper, provide informative fallback
        # In developer / offline mode, we note that the audio was captured asynchronously
        logger.info("voice_transcription_fallback_active")
        return f"[Voice input captured ({len(audio_bytes)} bytes) - Whisper backend endpoint at {self.base_url} did not return text]"
