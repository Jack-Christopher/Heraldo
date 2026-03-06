"""
PDF validation: page count, word count, quota.
Uses pypdf for fast estimation; pdfplumber for exact count on small PDFs.
"""
import gc
from typing import Tuple, Optional

import pdfplumber
from pypdf import PdfReader


# Max pages to process for exact count (avoids OOM on huge PDFs)
MAX_PAGES_FOR_EXACT = 50
# Pages to sample for fast estimation
SAMPLE_PAGES = 10
# Min pages to trigger estimation (otherwise exact)
MIN_PAGES_FOR_ESTIMATION = 15


def _get_page_count_fast(pdf_path: str) -> int:
    """Get page count with pypdf (lightweight, low memory)."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def _count_words_in_text(text: Optional[str]) -> int:
    return len(text.split()) if text and text.strip() else 0


def estimate_pdf_words(pdf_path: str) -> Tuple[int, int, bool]:
    """
    Fast word count by sampling pages. For PDFs with many pages.

    Returns:
        (page_count, estimated_word_count, is_estimate)
    """
    reader = PdfReader(pdf_path)
    page_count = len(reader.pages)
    if page_count == 0:
        return 0, 0, False

    if page_count <= SAMPLE_PAGES:
        # Small PDF: count all pages
        total = 0
        for i in range(page_count):
            text = reader.pages[i].extract_text()
            total += _count_words_in_text(text)
        return page_count, total, False

    # Sample first SAMPLE_PAGES (spread for variety if possible)
    step = max(1, page_count // SAMPLE_PAGES)
    indices = list(range(0, min(page_count, SAMPLE_PAGES * step), step))[:SAMPLE_PAGES]
    sample_words = 0
    sampled = 0
    for i in indices:
        if i >= page_count:
            break
        text = reader.pages[i].extract_text()
        sample_words += _count_words_in_text(text)
        sampled += 1
    if sampled == 0:
        return page_count, 0, True
    avg = sample_words / sampled
    estimated = int(avg * page_count)
    return page_count, estimated, True


def count_pdf_pages_and_words(
    pdf_path: str, max_pages: Optional[int] = None
) -> Tuple[int, int, bool]:
    """
    Count pages and words. Uses fast estimation for large PDFs to avoid
    timeout and OOM. For smaller PDFs uses exact count with pdfplumber.

    Returns:
        (page_count, word_count, is_estimated)
    """
    limit = max_pages or MAX_PAGES_FOR_EXACT
    page_count = _get_page_count_fast(pdf_path)
    if page_count == 0:
        return 0, 0, False

    # Use fast estimation for large PDFs (avoids pdfplumber memory/timeout)
    if page_count >= MIN_PAGES_FOR_ESTIMATION or page_count > limit:
        _, word_count, is_est = estimate_pdf_words(pdf_path)
        return page_count, word_count, is_est

    # Exact count for small PDFs - process page by page to limit memory
    word_count = 0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= limit:
                    break
                try:
                    text = page.extract_text()
                    if text:
                        word_count += _count_words_in_text(text)
                except Exception:
                    continue
    finally:
        gc.collect()
    return min(page_count, limit), word_count, False


def validate_pdf_limits(pdf_path: str, max_words: int) -> Tuple[bool, str, int, int, bool]:
    """
    Validate PDF against word limit.

    Returns:
        (valid, error_message, page_count, word_count, is_estimated)
    """
    try:
        page_count, word_count, is_estimated = count_pdf_pages_and_words(pdf_path)
    except MemoryError:
        return False, "El PDF usa demasiada memoria. Prueba con un archivo más pequeño.", 0, 0, False
    except Exception as e:
        return False, str(e) or "Error al procesar el PDF.", 0, 0, False

    if word_count > max_words:
        return False, f"El PDF tiene {word_count} palabras. Máximo permitido: {max_words}.", page_count, word_count, is_estimated

    return True, "", page_count, word_count, is_estimated
