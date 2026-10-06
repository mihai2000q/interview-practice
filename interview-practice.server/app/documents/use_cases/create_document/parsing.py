import io

from pypdf import PdfReader
from pypdf.errors import PyPdfError


class PdfParseError(Exception):
    """The upload isn't a readable, text-bearing PDF."""


def extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PdfParseError("Encrypted PDFs are not supported.")
        text = "\n".join(page.extract_text() for page in reader.pages).strip()
    except PdfParseError:
        raise
    except (PyPdfError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise PdfParseError("The file is not a valid PDF.") from exc
    if not text:
        # pypdf is not OCR software: a scanned PDF has no text layer to extract.
        raise PdfParseError("No text could be extracted (is it a scanned PDF?).")
    return text
