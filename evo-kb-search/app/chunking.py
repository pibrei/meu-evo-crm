import re


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Pack paragraphs into ~`size`-char chunks; hard-split paragraphs that are
    longer than `size`, keeping `overlap` chars between the hard splits."""
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""

    for p in paragraphs:
        if len(p) > size:
            if buf:
                chunks.append(buf)
                buf = ""
            step = max(1, size - overlap)
            start = 0
            while start < len(p):
                chunks.append(p[start : start + size])
                start += step
            continue

        if len(buf) + len(p) + 2 <= size:
            buf = f"{buf}\n\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            buf = p

    if buf:
        chunks.append(buf)

    return chunks
