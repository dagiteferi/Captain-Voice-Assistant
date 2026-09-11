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
        self._client = httpx.AsyncClient(timeout=15.0)

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
        """Translate text to target language via MyMemory API.

        Raises RuntimeError on failure so the pipeline records a genuine
        failure event rather than a silent passthrough.
        """
        source = (source_language.code if source_language else "en").replace("-", "_")
        target = target_language.code.replace("-", "_")

        # Skip translation when source == target
        if source == target:
            logger.debug("Source and target language are both '%s' — returning text unchanged.", source)
            return text

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

            # MyMemory sometimes returns the input unchanged for unsupported pairs
            if translated.strip() == text.strip() and len(text) > 10:
                logger.warning(
                    "[translate] MyMemory returned identical text for %s→%s — "
                    "this pair may not be supported. Proceeding anyway.",
                    source, target,
                )

            logger.info(
                "[translate] ✓ MyMemory %s→%s complete. Input=%d, Output=%d chars.",
                source, target, len(text), len(translated),
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
