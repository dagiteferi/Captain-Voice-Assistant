from domain.voice.entities import VoiceProfile


class FakeTTSAdapter:
    async def synthesize(self, text: str, voice_profile: VoiceProfile) -> bytes:
        body = text.encode("utf-8") or b"captain"
        data_size = len(body)
        header = bytearray(44)
        header[0:4] = b"RIFF"
        header[4:8] = (36 + data_size).to_bytes(4, "little")
        header[8:12] = b"WAVE"
        header[12:16] = b"fmt "
        header[16:20] = (16).to_bytes(4, "little")
        header[20:22] = (1).to_bytes(2, "little")
        header[22:24] = (1).to_bytes(2, "little")
        header[24:28] = (16000).to_bytes(4, "little")
        header[28:32] = (16000).to_bytes(4, "little")
        header[32:34] = (1).to_bytes(2, "little")
        header[34:36] = (8).to_bytes(2, "little")
        header[36:40] = b"data"
        header[40:44] = data_size.to_bytes(4, "little")
        return bytes(header) + body
