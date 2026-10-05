from io import BytesIO

from pypdf import PdfWriter

from app.knowledge.pdf_extractor import extract_pdf_pages


def test_extract_pdf_pages():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)

    pdf_buffer = BytesIO()
    writer.write(pdf_buffer)

    pages = extract_pdf_pages(pdf_buffer.getvalue())

    assert len(pages) == 1
    assert pages[0]["page_number"] == 1