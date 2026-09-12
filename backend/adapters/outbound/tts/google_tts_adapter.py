"""Google Cloud Text-to-Speech adapter via REST API.

Uses the texttospeech.googleapis.com/v1 endpoint.
Requires: GOOGLE_TTS_API_KEY in .env (same free Google Cloud project).

Free tier: 1 million characters/month (Standard) or 1 million/month (WaveNet).
"""

from __future__ import annotations

import base64
import logging

import httpx

from domain.voice.entities import VoiceProfile

logger = logging.getLogger(__name__)

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


class GoogleTTSAdapter:
    """Real TTS via Google Cloud Text-to-Speech REST API — free tier."""

    def __init__(
        self,
        api_key: str,
        voice_en: str = "en-US-Neural2-D",
        voice_am: str = "am-ET-Standard-A",
    ) -> None:
        if not api_key:
            raise ValueError(
                "GOOGLE_TTS_API_KEY is not set. Enable the Text-to-Speech API "
                "in Google Cloud Console and create an API key."
            )
        self._api_key = api_key
        self._voice_en = voice_en
        self._voice_am = voice_am
        self._client = httpx.AsyncClient(timeout=30.0)

    async def synthesize(
        self, text: str, voice_profile: VoiceProfile | None = None
    ) -> bytes:
        """Synthesize speech from text via Google Cloud TTS.

        Returns raw MP3 bytes.
        Raises RuntimeError on failure.
        """
        if not text or not text.strip():
            raise RuntimeError("TTS synthesis requested with empty text.")

        if voice_profile and getattr(voice_profile, "voice_id", None):
            voice_name = voice_profile.voice_id
        elif any("\u1200" <= char <= "\u137f" for char in text):
            voice_name = self._voice_am
        else:
            voice_name = self._voice_en

        parts = voice_name.split("-")
        language_code = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else "en-US"

        logger.info(
            "[tts] Google Cloud TTS: voice=%s, lang=%s, text len=%d chars...",
            voice_name, language_code, len(text),
        )

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": language_code,
                "name": voice_name,
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
                "pitch": 0.0,
            },
        }

        try:
            response = await self._client.post(
                GOOGLE_TTS_URL,
                json=payload,
                params={"key": self._api_key},
            )
            response.raise_for_status()
            data = response.json()

            audio_b64 = data.get("audioContent", "")
            if not audio_b64:
                raise RuntimeError(
                    f"Google TTS returned empty audioContent. Response: {data}"
                )

            audio_bytes = base64.b64decode(audio_b64)
            if not audio_bytes:
                raise RuntimeError("Google TTS: base64 decode produced empty bytes.")

            logger.info(
                "[tts] ✓ Google TTS complete. Voice=%s, audio=%d bytes (~%.1fs).",
                voice_name,
                len(audio_bytes),
                len(audio_bytes) / 16000,
            )
            return audio_bytes

        except RuntimeError:
            raise
        except httpx.HTTPStatusError as e:
            body = e.response.text[:400]
            raise RuntimeError(
                f"Google TTS API HTTP {e.response.status_code}: {body}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Google TTS synthesis failed: {e}") from e

    async def aclose(self) -> None:
        await self._client.aclose()
