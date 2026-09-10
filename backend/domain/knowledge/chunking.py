def split_content(content: str, max_chars: int = 800, overlap: int = 80) -> list[str]:
    text = " ".join(content.split())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars")

    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        parts.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return parts
