from uuid import uuid4

import pytest

from domain.conversation.value_objects import Language
from domain.exceptions import MissingVoiceProfileError
from domain.voice.entities import CAPTAIN_PRESET, AudioResponse, Translation, VoiceProfile


def test_audio_response_requires_voice_profile() -> None:
    with pytest.raises(MissingVoiceProfileError):
        AudioResponse.create(
            translation_id=uuid4(),
            voice_profile=None,
            audio_path="/tmp/out.wav",
        )


def test_audio_response_binds_preset_voice() -> None:
    audio = AudioResponse.create(
        translation_id=uuid4(),
        voice_profile=CAPTAIN_PRESET,
        audio_path="/tmp/captain.wav",
        duration_ms=1200,
    )
    assert audio.voice_profile_id == CAPTAIN_PRESET.id
    assert audio.duration_ms == 1200


def test_translation_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        Translation(
            answer_id=uuid4(),
            target_language=Language("am"),
            translated_text=" ",
        )


def test_voice_profile_carries_language() -> None:
    profile = VoiceProfile(name="bridge", language=Language("en"))
    assert profile.language.code == "en"
