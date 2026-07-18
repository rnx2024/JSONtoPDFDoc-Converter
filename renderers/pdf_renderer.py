from weasyprint import CSS, HTML

from schemas import Margin


def html_to_pdf_bytes(html: str, margin: Margin) -> bytes:
    page_css = CSS(
        string=(
            "@page { size: A4; "
            f"margin: {margin.top}mm {margin.right}mm {margin.bottom}mm {margin.left}mm; }}"
        )
    )
    return HTML(string=html).write_pdf(stylesheets=[page_css])
