import pdfkit

from config import PDF_OPTIONS, PDFKIT_CONFIG
from schemas import Margin


def html_to_pdf_bytes(html: str, margin: Margin) -> bytes:
    options = {
        **PDF_OPTIONS,
        "margin-top": f"{margin.top}mm",
        "margin-right": f"{margin.right}mm",
        "margin-bottom": f"{margin.bottom}mm",
        "margin-left": f"{margin.left}mm",
    }
    return pdfkit.from_string(
        html,
        False,
        configuration=PDFKIT_CONFIG,
        options=options,
    )
