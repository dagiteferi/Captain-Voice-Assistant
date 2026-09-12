"""Free translation adapter using MyMemory API.

MyMemory is completely free (no API key required) for up to 1000 requests/day.
Falls back to a usage-limited anonymous endpoint.
For higher limits, set MYMEMORY_EMAIL in .env.

API docs: https://mymemory.translated.net/doc/spec.php
"""

from __future__ import annotations

import logging

import httpx

from domain.conversation.value_objects import Language

logger = logging.getLogger(__name__)

MYMEMORY_API_URL = "https://api.mymemory.translated.net/get"


class MyMemoryTranslateAdapter:
    """Free online translation via MyMemory REST API — no API key needed."""

    def __init__(self, email: str = "") -> None:
        self._email = email
        self._client = httpx.AsyncClient(timeout=8.0)

    async def initialize(self) -> None:
        """No startup work needed — API is stateless."""
        logger.info("[SETUP] MyMemory Translate adapter ready (no setup required).")

    async def translate(
        self,
        text: str,
        target_language: Language,
        *,
        source_language: Language | None = None,
    ) -> str:
        """Translate text to target language via MyMemory API with auto-chunking for long text."""
        source = (source_language.code if source_language else "en").replace("-", "_")
        target = target_language.code.replace("-", "_")

        # Skip translation when source == target
        if source == target:
            logger.debug("Source and target language are both '%s' — returning text unchanged.", source)
            return text

        # Split long text into <= 450 character chunks to respect MyMemory limit
        if len(text) > 450:
            paragraphs = [p for p in text.split("\n") if p.strip()]
            translated_parts: list[str] = []
            for p in paragraphs:
                if len(p) <= 450:
                    tr = await self._translate_single(p, source, target)
                    translated_parts.append(tr)
                else:
                    # Split long paragraph by sentence or period
                    sentences = p.split(". ")
                    sub_buf = ""
                    for s in sentences:
                        s_item = s if s.endswith(".") else f"{s}."
                        if len(sub_buf) + len(s_item) + 1 <= 450:
                            sub_buf = f"{sub_buf} {s_item}".strip()
                        else:
                            if sub_buf:
                                translated_parts.append(await self._translate_single(sub_buf, source, target))
                            sub_buf = s_item
                    if sub_buf:
                        translated_parts.append(await self._translate_single(sub_buf, source, target))
            return "\n".join(translated_parts)
        else:
            return await self._translate_single(text, source, target)

    async def _translate_single(self, text: str, source: str, target: str) -> str:
        params: dict[str, str] = {
            "q": text,
            "langpair": f"{source}|{target}",
        }
        if self._email:
            params["de"] = self._email

        logger.info(
            "[translate] MyMemory: %s→%s, input len=%d chars...",
            source, target, len(text),
        )

        try:
            response = await self._client.get(MYMEMORY_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            status = data.get("responseStatus")
            if status != 200:
                error_msg = data.get("responseDetails", "Unknown error")
                raise RuntimeError(
                    f"MyMemory API error (status={status}): {error_msg}"
                )

            translated = data.get("responseData", {}).get("translatedText", "")
            if not translated:
                raise RuntimeError(
                    f"MyMemory returned empty translation for {source}→{target}."
                )

            return translated.strip()

        except RuntimeError:
            raise
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"MyMemory API HTTP {e.response.status_code}: {e.response.text[:300]}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"MyMemory translate() failed: {e}") from e


    async def aclose(self) -> None:
        await self._client.aclose()
