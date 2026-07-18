import os

import pdfkit
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

WKHTMLTOPDF_PATH: str | None = os.getenv("WKHTMLTOPDF_PATH")
PDFKIT_CONFIG = (
    pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
    if WKHTMLTOPDF_PATH else None
)

PDF_OPTIONS = {
    "print-media-type": None,
    "enable-local-file-access": None,
    "page-size": "A4",
}
