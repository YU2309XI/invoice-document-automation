from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


OUTPUT_DIR = Path("data/invoices")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_standard_invoice(
    filename,
    vendor,
    invoice_number,
    invoice_date,
    due_date,
    customer,
    items,
    tax_rate,
    forced_total=None,
):
    """Generate a standard USD text-based invoice."""

    file_path = OUTPUT_DIR / filename

    c = canvas.Canvas(
        str(file_path),
        pagesize=LETTER,
    )

    _, height = LETTER

    # Header
    c.setFont("Helvetica-Bold", 22)
    c.drawString(
        50,
        height - 60,
        "INVOICE",
    )

    c.setFont("Helvetica-Bold", 12)
    c.drawString(
        50,
        height - 100,
        vendor,
    )

    c.setFont("Helvetica", 10)
    c.drawString(
        50,
        height - 118,
        "1450 Market Street",
    )
    c.drawString(
        50,
        height - 134,
        "San Francisco, CA 94102",
    )
    c.drawString(
        50,
        height - 150,
        "billing@example.com",
    )

    # Invoice metadata
    c.setFont("Helvetica-Bold", 10)

    c.drawString(
        400,
        height - 100,
        "Invoice #:",
    )
    c.drawString(
        400,
        height - 120,
        "Invoice Date:",
    )
    c.drawString(
        400,
        height - 140,
        "Due Date:",
    )

    c.setFont("Helvetica", 10)

    c.drawString(
        465,
        height - 100,
        invoice_number,
    )
    c.drawString(
        465,
        height - 120,
        invoice_date,
    )
    c.drawString(
        465,
        height - 140,
        due_date,
    )

    # Customer
    c.setFont("Helvetica-Bold", 11)
    c.drawString(
        50,
        height - 200,
        "Bill To",
    )

    c.setFont("Helvetica", 10)
    c.drawString(
        50,
        height - 220,
        customer,
    )
    c.drawString(
        50,
        height - 236,
        "220 King Street",
    )
    c.drawString(
        50,
        height - 252,
        "Seattle, WA 98104",
    )

    # Table
    y = height - 310

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Description")
    c.drawString(300, y, "Qty")
    c.drawString(365, y, "Unit Price")
    c.drawString(480, y, "Amount")

    y -= 25
    c.setFont("Helvetica", 10)

    subtotal = 0

    for description, qty, unit_price in items:
        amount = qty * unit_price
        subtotal += amount

        c.drawString(
            50,
            y,
            description,
        )
        c.drawString(
            305,
            y,
            str(qty),
        )
        c.drawRightString(
            430,
            y,
            f"${unit_price:,.2f}",
        )
        c.drawRightString(
            535,
            y,
            f"${amount:,.2f}",
        )

        y -= 22

    tax = subtotal * tax_rate

    if forced_total is None:
        total = subtotal + tax
    else:
        total = forced_total

    # Totals
    y -= 20

    c.drawRightString(
        460,
        y,
        "Subtotal:",
    )
    c.drawRightString(
        535,
        y,
        f"${subtotal:,.2f}",
    )

    y -= 20

    c.drawRightString(
        460,
        y,
        f"Tax ({tax_rate * 100:g}%):",
    )
    c.drawRightString(
        535,
        y,
        f"${tax:,.2f}",
    )

    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(
        460,
        y,
        "Total:",
    )
    c.drawRightString(
        535,
        y,
        f"${total:,.2f}",
    )

    c.setFont("Helvetica", 9)
    c.drawString(
        50,
        70,
        "Thank you for your business.",
    )

    c.save()

    print(f"Created: {file_path}")


def generate_eur_invoice():
    """Generate the alternate EUR invoice layout."""

    file_path = OUTPUT_DIR / "invoice_002.pdf"

    c = canvas.Canvas(
        str(file_path),
        pagesize=LETTER,
    )

    _, height = LETTER

    c.setFont("Helvetica-Bold", 22)
    c.drawString(
        50,
        height - 60,
        "TAX INVOICE",
    )

    c.setFont("Helvetica-Bold", 13)
    c.drawString(
        50,
        height - 100,
        "Lumiere Design Studio",
    )

    c.setFont("Helvetica", 10)
    c.drawString(
        50,
        height - 118,
        "28 Rue Victor Hugo",
    )
    c.drawString(
        50,
        height - 134,
        "75008 Paris, France",
    )
    c.drawString(
        50,
        height - 150,
        "accounts@lumiere.example",
    )

    c.setFont("Helvetica-Bold", 10)
    c.drawString(
        360,
        height - 100,
        "Invoice Number",
    )
    c.drawString(
        360,
        height - 120,
        "Issue Date",
    )
    c.drawString(
        360,
        height - 140,
        "Payment Due",
    )

    c.setFont("Helvetica", 10)
    c.drawString(
        465,
        height - 100,
        "LD-2026-8842",
    )
    c.drawString(
        465,
        height - 120,
        "September 12, 2026",
    )
    c.drawString(
        465,
        height - 140,
        "October 12, 2026",
    )

    c.setFont("Helvetica-Bold", 11)
    c.drawString(
        50,
        height - 200,
        "Customer",
    )

    c.setFont("Helvetica", 10)
    c.drawString(
        50,
        height - 220,
        "Bluewave Media Ltd",
    )
    c.drawString(
        50,
        height - 236,
        "14 Oxford Street",
    )
    c.drawString(
        50,
        height - 252,
        "London, United Kingdom",
    )

    y = height - 310

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Service")
    c.drawString(300, y, "Hours")
    c.drawString(365, y, "Rate")
    c.drawString(480, y, "Line Total")

    items = [
        ("Brand Design", 4, 50.00),
        ("Website Graphics", 3, 60.00),
    ]

    y -= 25
    c.setFont("Helvetica", 10)

    subtotal = 0

    for description, qty, unit_price in items:
        amount = qty * unit_price
        subtotal += amount

        c.drawString(50, y, description)
        c.drawString(305, y, str(qty))
        c.drawRightString(
            430,
            y,
            f"EUR {unit_price:,.2f}",
        )
        c.drawRightString(
            535,
            y,
            f"EUR {amount:,.2f}",
        )

        y -= 22

    vat = subtotal * 0.20
    total = subtotal + vat

    y -= 20

    c.drawRightString(
        460,
        y,
        "Net Amount",
    )
    c.drawRightString(
        535,
        y,
        f"EUR {subtotal:,.2f}",
    )

    y -= 20

    c.drawRightString(
        460,
        y,
        "VAT 20%",
    )
    c.drawRightString(
        535,
        y,
        f"EUR {vat:,.2f}",
    )

    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(
        460,
        y,
        "Amount Due",
    )
    c.drawRightString(
        535,
        y,
        f"EUR {total:,.2f}",
    )

    c.setFont("Helvetica", 9)
    c.drawString(
        50,
        70,
        "Payment terms: 30 days.",
    )

    c.save()

    print(f"Created: {file_path}")


def generate_scanned_invoice():
    """Generate an image-only PDF for OCR testing."""

    image_path = (
        OUTPUT_DIR / "invoice_005_scan.png"
    )

    pdf_path = (
        OUTPUT_DIR / "invoice_005.pdf"
    )

    image = Image.new(
        "RGB",
        (1654, 2339),
        "white",
    )

    draw = ImageDraw.Draw(image)

    font_path = (
        "/System/Library/Fonts/Helvetica.ttc"
    )

    font_regular = ImageFont.truetype(
        font_path,
        34,
    )

    font_bold = ImageFont.truetype(
        font_path,
        38,
    )

    font_title = ImageFont.truetype(
        font_path,
        64,
    )

    draw.text(
        (120, 100),
        "INVOICE",
        fill="black",
        font=font_title,
    )

    draw.text(
        (120, 220),
        "Silverline Technology Services",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (120, 280),
        "725 Market Avenue",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (120, 330),
        "Portland, OR 97205",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (120, 380),
        "billing@silverline.example",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (950, 220),
        "Invoice #:",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (1200, 220),
        "INV-5005",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (950, 280),
        "Invoice Date:",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (1200, 280),
        "09/16/2026",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (950, 340),
        "Due Date:",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (1200, 340),
        "10/16/2026",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (120, 540),
        "Bill To",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (120, 600),
        "Oakridge Digital LLC",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (120, 650),
        "180 Lake Street",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (120, 700),
        "Chicago, IL 60601",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (120, 900),
        "Description",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (850, 900),
        "Qty",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (1050, 900),
        "Unit Price",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (1400, 900),
        "Amount",
        fill="black",
        font=font_bold,
    )

    items = [
        (
            "Cloud Setup",
            "1",
            "$250.00",
            "$250.00",
        ),
        (
            "Technical Support",
            "4",
            "$75.00",
            "$300.00",
        ),
    ]

    y = 980

    for description, qty, price, amount in items:
        draw.text(
            (120, y),
            description,
            fill="black",
            font=font_regular,
        )

        draw.text(
            (870, y),
            qty,
            fill="black",
            font=font_regular,
        )

        draw.text(
            (1050, y),
            price,
            fill="black",
            font=font_regular,
        )

        draw.text(
            (1400, y),
            amount,
            fill="black",
            font=font_regular,
        )

        y += 80

    draw.text(
        (1050, 1350),
        "Subtotal:",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (1400, 1350),
        "$550.00",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (1050, 1420),
        "Tax (8%):",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (1400, 1420),
        "$44.00",
        fill="black",
        font=font_regular,
    )

    draw.text(
        (1050, 1500),
        "Total:",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (1400, 1500),
        "$594.00",
        fill="black",
        font=font_bold,
    )

    draw.text(
        (120, 2100),
        "Thank you for your business.",
        fill="black",
        font=font_regular,
    )

    image.save(image_path)

    image.save(
        pdf_path,
        "PDF",
        resolution=150.0,
    )

    print(f"Created: {image_path}")
    print(f"Created: {pdf_path}")


def main():
    # 001: Valid USD text PDF
    generate_standard_invoice(
        filename="invoice_001.pdf",
        vendor="Northstar Office Supplies",
        invoice_number="INV-1001",
        invoice_date="09/10/2026",
        due_date="10/10/2026",
        customer="BrightPath Consulting LLC",
        items=[
            ("Wireless Keyboard", 2, 45.00),
            ("USB-C Dock", 1, 129.00),
            ("Laptop Stand", 3, 38.00),
        ],
        tax_rate=0.085,
    )

    # 002: Alternate EUR layout
    generate_eur_invoice()

    # 003: Deliberately incorrect total
    generate_standard_invoice(
        filename="invoice_003.pdf",
        vendor="Apex Workspace Solutions",
        invoice_number="INV-3003",
        invoice_date="09/15/2026",
        due_date="10/15/2026",
        customer="Greenfield Operations Inc",
        items=[
            ("Office Chairs", 4, 100.00),
            ("Desk Lamps", 2, 50.00),
        ],
        tax_rate=0.08,
        forced_total=590.00,
    )

    # 004: Deliberately missing invoice number
    generate_standard_invoice(
        filename="invoice_004.pdf",
        vendor="Cedar Print Company",
        invoice_number="",
        invoice_date="09/10/2026",
        due_date="10/10/2026",
        customer="Summit Events LLC",
        items=[
            ("Wireless Keyboard", 2, 45.00),
            ("USB-C Dock", 1, 129.00),
            ("Laptop Stand", 3, 38.00),
        ],
        tax_rate=0.085,
    )

    # 005: Image-only scanned PDF
    generate_scanned_invoice()

    print("\nAll sample invoices created.")


if __name__ == "__main__":
    main()
