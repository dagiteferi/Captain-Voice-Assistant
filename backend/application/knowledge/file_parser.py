"""File and URL content extractor utility for multi-format knowledge submissions.

Supports:
- PDF (.pdf)
- Word Documents (.docx, .doc)
- PowerPoint (.pptx, .ppt)
- Text / Markdown (.txt, .md)
- JSON (.json)
- CSV (.csv)
- Web URLs (HTML to plain text)
"""

from __future__ import annotations

import io
import re
import logging
import httpx

logger = logging.getLogger(__name__)


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    """Extract plain text content from uploaded file bytes based on file extension."""
    fname = filename.lower()

    # 1. PDF
    if fname.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for idx, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt:
                    pages_text.append(f"--- Page {idx + 1} ---\n{txt}")
            text = "\n\n".join(pages_text).strip()
            if text:
                return text
        except Exception as e:
            logger.warning("[file_parser] pypdf failed: %s", e)

    # 2. Word DOCX
    if fname.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs).strip()
            if text:
                return text
        except Exception as e:
            logger.warning("[file_parser] python-docx failed: %s", e)

    # 3. PowerPoint PPTX
    if fname.endswith(".pptx"):
        try:
            import pptx
            prs = pptx.Presentation(io.BytesIO(file_bytes))
            slides_text = []
            for idx, slide in enumerate(prs.slides):
                slide_lines = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_lines.append(shape.text.strip())
                if slide_lines:
                    slides_text.append(f"--- Slide {idx + 1} ---\n" + "\n".join(slide_lines))
            text = "\n\n".join(slides_text).strip()
            if text:
                return text
        except Exception as e:
            logger.warning("[file_parser] python-pptx failed: %s", e)

    # 4. Text, Markdown, CSV, JSON, HTML fallbacks
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            raw_text = file_bytes.decode(encoding)
            # If it's HTML, clean HTML tags
            if "<html" in raw_text.lower() or "<body" in raw_text.lower():
                return clean_html_to_text(raw_text)
            return raw_text.strip()
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not extract text from file '{filename}'. Unsupported or corrupted binary format.")


async def extract_text_from_url(url: str) -> str:
    """Fetch content from a web URL and extract plain text."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Captain Voice Assistant KB Ingest Bot)"
        }
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        raw_html = response.text

    text = clean_html_to_text(raw_html)
    if not text.strip():
        raise ValueError(f"No text content could be extracted from URL: {url}")
    return text.strip()


def clean_html_to_text(html: str) -> str:
    """Strip HTML tags, scripts, styles and format into readable plain text."""
    # Remove script and style elements
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Convert breaks and paragraphs to newlines
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</h[1-6]>", "\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</li>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Replace HTML entities
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&amp;", "&", text)
    # Clean multiple spaces and blank lines
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = [line for line in lines if line]
    return "\n".join(clean_lines)
