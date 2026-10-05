from io import BytesIO

from pypdf import PdfReader


def extract_pdf_pages(file_content: bytes) -> list[dict]:
    reader = PdfReader(BytesIO(file_content))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append(
            {
                "page_number": page_number,
                "text": text,
            }
        )

    return pages