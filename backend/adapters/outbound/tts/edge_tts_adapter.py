"""Real Edge TTS adapter using Microsoft Edge Speech Service.

Raises explicitly on empty output or synthesis errors so the pipeline
trace records AudioSynthesized only when real audio bytes are produced.
"""

import logging
import tempfile
from pathlib import Path

from domain.voice.entities import VoiceProfile

logger = logging.getLogger(__name__)


class EdgeTTSAdapter:
    """Real online TTS using edge-tts (Microsoft Edge Speech Service)."""

    def __init__(self, default_voice: str = "en-US-ChristopherNeural"):
        self.default_voice = default_voice

    async def synthesize(self, text: str, voice_profile: VoiceProfile | None = None) -> bytes:
        """Synthesize real audio speech from text.

        Returns raw MP3 bytes on success.
        Raises RuntimeError on empty output or synthesis error — the caller
        (orchestrator node) must catch this and record a pipeline failure,
        NOT emit a false AudioSynthesized success event.
        """
        if not text or not text.strip():
            raise RuntimeError(
                "TTS synthesis requested with empty text — nothing to synthesize."
            )

        voice = self.default_voice
        if voice_profile and getattr(voice_profile, "voice_id", None):
            voice = voice_profile.voice_id
        elif any("\u1200" <= char <= "\u137f" for char in text):
            voice = "am-ET-MekdesNeural"
        logger.info("Using TTS voice: %s", voice)

        try:
            import edge_tts
        except ImportError as e:
            raise RuntimeError(
                "edge-tts is not installed. Install with: pip install edge-tts>=6.1.9"
            ) from e

        logger.info(
            "Synthesizing %d chars of text with voice '%s'...", len(text), voice
        )

        try:
            communicate = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = Path(f.name)

            await communicate.save(str(temp_path))
            audio_bytes = temp_path.read_bytes()
            temp_path.unlink(missing_ok=True)

            if not audio_bytes:
                raise RuntimeError(
                    f"Edge TTS returned empty audio for voice '{voice}'. "
                    "This is a synthesis failure, not a success."
                )

            logger.info(
                "✓ TTS synthesis complete. Voice='%s', audio size=%d bytes (~%.1fs).",
                voice,
                len(audio_bytes),
                # rough estimate: MP3 at 128kbps → 16000 bytes/sec
                len(audio_bytes) / 16000,
            )
            return audio_bytes

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Edge TTS synthesis failed for voice '{voice}': {e}") from e
