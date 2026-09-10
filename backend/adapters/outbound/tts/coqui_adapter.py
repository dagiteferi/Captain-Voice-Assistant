"""Coqui-based local TTS adapter."""

from domain.voice.entities import VoiceProfile


class CoquiTTSAdapter:
    """Local TTS using Coqui TTS."""

    def __init__(self):
        try:
            from TTS.api import TTS
            self.tts_engine = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", gpu=False)
        except ImportError:
            self.tts_engine = None

    async def synthesize(self, text: str, voice_profile: VoiceProfile) -> bytes:
        """Synthesize speech from text."""
        if not self.tts_engine:
            # Fallback: return empty bytes if TTS engine not initialized
            return b""

        try:
            # Save to temp file and read bytes
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            self.tts_engine.tts_to_file(text, file_path=temp_path)

            with open(temp_path, "rb") as f:
                audio_bytes = f.read()

            import os
            os.unlink(temp_path)

            return audio_bytes
        except Exception:
            return b""

