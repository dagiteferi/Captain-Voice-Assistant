"""Local translation adapter using Argos Translate.

Language packs are downloaded eagerly at startup via initialize().
Translation failures raise explicitly rather than silently returning the
original text — this ensures the pipeline trace records a real failure
rather than a false 'TranslationCompleted' success.
"""

import logging

from domain.conversation.value_objects import Language

logger = logging.getLogger(__name__)


class ArgosTranslateAdapter:
    """Adapter for offline translation using Argos Translate."""

    def __init__(self):
        self._argos_translate = None
        self._argos_package = None
        self._initialized = False
        self._init_error: str | None = None

        try:
            import argostranslate.package
            import argostranslate.translate
            self._argos_translate = argostranslate.translate
            self._argos_package = argostranslate.package
            logger.info("Argos Translate library loaded successfully.")
        except ImportError as e:
            self._init_error = str(e)
            logger.error(
                "argostranslate is not installed — translation will be unavailable. "
                "Install with: pip install argostranslate>=1.9.0"
            )

    async def initialize(self) -> None:
        """Download required language packs at startup if missing.

        Called by the FastAPI lifespan hook so packs are ready before any
        request arrives. Logs clearly to the console during setup.
        """
        if self._argos_package is None:
            logger.error(
                "[SETUP] argostranslate not installed. "
                "Translation stage will FAIL on every request until it is installed."
            )
            return

        logger.info("[SETUP] Checking Argos Translate language packs...")

        try:
            logger.info("[SETUP] Updating Argos package index (network request)...")
            self._argos_package.update_package_index()
            available_packages = self._argos_package.get_available_packages()
            logger.info(
                "[SETUP] Package index updated. %d packages available.",
                len(available_packages),
            )
        except Exception as e:
            logger.error("[SETUP] Failed to update Argos package index: %s", e)
            logger.warning(
                "[SETUP] Will attempt to use already-installed packs if any exist."
            )
            available_packages = []

        required_pairs = [("en", "am"), ("am", "en")]
        for source, target in required_pairs:
            installed = self._argos_package.get_installed_packages()
            has_pack = any(
                p.from_code == source and p.to_code == target for p in installed
            )
            if has_pack:
                logger.info(
                    "[SETUP] Language pack %s → %s already installed. ✓", source, target
                )
                continue

            logger.info(
                "[SETUP] Language pack %s → %s is MISSING — downloading now...",
                source,
                target,
            )
            pack = next(
                (
                    p
                    for p in available_packages
                    if p.from_code == source and p.to_code == target
                ),
                None,
            )
            if pack:
                try:
                    pack.install()
                    logger.info(
                        "[SETUP] ✓ Installed language pack %s → %s.", source, target
                    )
                except Exception as e:
                    logger.error(
                        "[SETUP] ✗ Failed to install language pack %s → %s: %s",
                        source,
                        target,
                        e,
                    )
            else:
                logger.error(
                    "[SETUP] ✗ Language pack %s → %s not found in Argos index. "
                    "Translation to/from this pair will FAIL at runtime.",
                    source,
                    target,
                )

        self._initialized = True
        logger.info("[SETUP] Argos Translate initialization complete.")

    async def translate(
        self,
        text: str,
        target_language: Language,
        *,
        source_language: Language | None = None,
    ) -> str:
        """Translate text to target language.

        Raises RuntimeError on failure so the pipeline records a genuine
        failure event rather than a silent passthrough that looks like success.
        """
        if self._argos_translate is None:
            raise RuntimeError(
                f"argostranslate is not installed (import error: {self._init_error}). "
                "Cannot perform translation."
            )

        if not self._initialized:
            logger.warning(
                "ArgosTranslateAdapter.translate() called before initialize() — "
                "language packs may not be ready."
            )

        source = (source_language.code if source_language else "en").replace("-", "_")
        target = target_language.code.replace("-", "_")

        # Skip translation when source == target (no-op, not a failure)
        if source == target:
            logger.debug(
                "Source and target language are both '%s' — returning text unchanged.", source
            )
            return text

        try:
            translated = self._argos_translate.translate(text, source, target)
            result = translated.strip()

            # Guard: if Argos returns the exact same text for a non-trivial input,
            # it most likely silently failed (no pack, wrong language code, etc.).
            # Raise so the pipeline trace shows a genuine failure.
            if result == text and len(text) > 10:
                raise RuntimeError(
                    f"Argos returned untranslated text for {source}→{target} "
                    f"(output identical to input — likely missing language pack). "
                    f"Input snippet: '{text[:60]}...'"
                )

            logger.info(
                "Translation %s→%s complete. Input len=%d, Output len=%d.",
                source,
                target,
                len(text),
                len(result),
            )
            return result

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Argos Translate failed for {source}→{target}: {e}"
            ) from e
