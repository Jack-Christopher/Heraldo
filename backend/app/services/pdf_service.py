"""
PDF validation: page count, word count, quota.
"""
import pdfplumber


def count_pdf_pages_and_words(pdf_path: str):
    """
    Count pages and words in a PDF.

    Returns:
        (page_count, word_count)
    """
    page_count = 0
    word_count = 0
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            try:
                text = page.extract_text()
                if text:
                    words = text.split()
                    word_count += len(words)
            except Exception:
                continue
    return page_count, word_count


def validate_pdf_limits(pdf_path: str, max_pages: int, max_words: int):
    """
    Validate PDF against page and word limits.

    Returns:
        (valid, error_message, page_count, word_count)
        If valid is False, error_message explains why.
    """
    try:
        page_count, word_count = count_pdf_pages_and_words(pdf_path)
    except Exception as e:
        return False, str(e), 0, 0

    if page_count > max_pages:
        return False, f"El PDF tiene {page_count} páginas. Máximo permitido: {max_pages}.", page_count, word_count
    if word_count > max_words:
        return False, f"El PDF tiene {word_count} palabras. Máximo permitido: {max_words} (equivalente a ~5 páginas estándar).", page_count, word_count

    return True, "", page_count, word_count
