from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_CONTEXT_CHARS = 120_000


def _truncate(text: str) -> str:
    if len(text) <= MAX_CONTEXT_CHARS:
        return text
    return text[:MAX_CONTEXT_CHARS] + "\n\n[... truncated for context limit ...]"


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data), strict=False)
    except PdfReadError as e:
        raise ValueError(f"Invalid or unreadable PDF: {e}") from e
    parts: list[str] = []
    try:
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    except Exception as e:
        raise ValueError(f"Could not extract text from PDF: {e}") from e
    return "\n\n".join(parts)


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File is too large (max 5MB)")

    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            text = _pdf_text(data)
        else:
            text = data.decode("utf-8", errors="replace")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not read file: {e}") from e

    text = text.strip()
    if not text:
        raise ValueError("Could not read any text from the file")

    return _truncate(text)
