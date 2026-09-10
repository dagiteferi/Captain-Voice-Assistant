from domain.knowledge.chunking import split_content


def test_split_content_keeps_short_text_intact() -> None:
    text = "Standing heading is two seven zero true."
    assert split_content(text) == [text]


def test_split_content_windows_long_text() -> None:
    text = "alpha " * 50
    parts = split_content(text, max_chars=40, overlap=10)
    assert len(parts) > 1
    assert all(len(part) <= 40 for part in parts)
    assert parts[0][:10] == text[:10]


def test_split_content_rejects_empty() -> None:
    assert split_content("   ") == []
