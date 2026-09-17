"""Extract structured fields from raw invoice text.

The parser reports what it could not determine rather than guessing. Where a
value is genuinely ambiguous — most often a numeric date — it is recorded as a
warning so the invoice is routed for review instead of silently carrying a
plausible but wrong value into the report.
"""

import re
from datetime import date, datetime

# Textual dates are unambiguous, so they are parsed directly.
TEXT_DATE_FORMATS = [
    "%B %d, %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%Y-%m-%d",
]

NUMERIC_DATE_RE = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")

# Checked in order: the dollar sign is the least specific, so it goes last.
CURRENCY_MARKERS = [
    ("EUR", ("€", "EUR")),
    ("GBP", ("£", "GBP")),
    ("USD", ("US$", "USD", "$")),
]

CURRENCY_STRIP = ["US$", "EUR", "GBP", "USD", "€", "£", "$", ","]

INVOICE_NUMBER_PATTERNS = [
    r"INV-\d+",
    r"[A-Z]{2}-\d{4}-\d+",
]

# Label-based fallback for formats the patterns above do not cover,
# e.g. "Invoice No. 2026/0042" or "Invoice Number: ABC123".
INVOICE_NUMBER_LABEL_RE = re.compile(
    r"Invoice\s*(?:No\.?|Number|#)\s*:?\s*([A-Za-z0-9][A-Za-z0-9/\-]*)",
    re.IGNORECASE,
)

MONEY_RE = re.compile(r"(?:€|£|US\$|\$|EUR\s*|GBP\s*|USD\s*)[\d,]+\.\d{2}")


def normalize_date(value, date_order=None):
    """Convert a date string to ISO format.

    Returns (iso_date, ambiguous). A numeric date like 03/04/2026 is valid
    under both US and European conventions and means different things in each.
    When one component exceeds 12 the value settles its own order. Otherwise
    it is ambiguous unless the caller has declared which convention applies —
    a client who says "our invoices are European" has resolved it, and
    flagging every date after that would be noise rather than diligence.
    """
    value = value.strip()

    match = NUMERIC_DATE_RE.match(value)
    if match:
        first, second, year = (int(part) for part in match.groups())

        if first > 12 and second <= 12:
            day, month, ambiguous = first, second, False
        elif second > 12 and first <= 12:
            month, day, ambiguous = first, second, False
        elif first <= 12 and second <= 12:
            if date_order == "DMY":
                day, month = first, second
            else:
                month, day = first, second
            # 05/05/2026 reads the same either way, and a declared convention
            # removes the question entirely.
            ambiguous = first != second and date_order is None
        else:
            return None, False

        try:
            return date(year, month, day).isoformat(), ambiguous
        except ValueError:
            return None, False

    for date_format in TEXT_DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, date_format)
            return parsed.strftime("%Y-%m-%d"), False
        except ValueError:
            continue

    return None, False


def parse_money(value):
    cleaned = value
    for token in CURRENCY_STRIP:
        cleaned = cleaned.replace(token, "")

    try:
        return float(cleaned.strip())
    except ValueError:
        return None


def detect_currency(lines):
    text = " ".join(lines)
    for code, markers in CURRENCY_MARKERS:
        if any(marker in text for marker in markers):
            return code
    return None


def _find_invoice_number(lines):
    for line in lines:
        for pattern in INVOICE_NUMBER_PATTERNS:
            match = re.search(pattern, line)
            if match:
                return match.group(0)

    for line in lines:
        match = INVOICE_NUMBER_LABEL_RE.search(line)
        if match:
            return match.group(1)

    return None


def _find_vendor(lines):
    for header in ("INVOICE", "TAX INVOICE"):
        if header in lines:
            index = lines.index(header)
            if index + 1 < len(lines):
                return lines[index + 1]

    # OCR output often collapses the header onto one line, e.g.
    # "Silverline Technology Services Invoice #: INV-5005"
    for line in lines:
        if re.search(r"Invoice\s*#\s*:", line, re.IGNORECASE):
            vendor = re.split(r"Invoice\s*#\s*:", line, flags=re.IGNORECASE)[0]
            if vendor.strip():
                return vendor.strip()

    return None


def _find_customer(lines):
    for label in ("Bill To", "Customer"):
        if label in lines:
            index = lines.index(label)
            if index + 1 < len(lines):
                return lines[index + 1]
    return None


def _find_money(lines, labels):
    for index, line in enumerate(lines):
        for label in labels:
            if not line.startswith(label):
                continue

            remainder = line[len(label):].strip()
            if remainder:
                value = parse_money(remainder)
                if value is not None:
                    return value

            # Some layouts put the label and the amount on separate lines.
            if index + 1 < len(lines):
                value = parse_money(lines[index + 1])
                if value is not None:
                    return value

    return None


def _find_tax(lines):
    for index, line in enumerate(lines):
        if not (line.startswith("Tax") or line.startswith("VAT")):
            continue

        # A tax line often carries a percentage as well as an amount;
        # the amount is the last money-shaped token on the line.
        amounts = MONEY_RE.findall(line)
        if amounts:
            return parse_money(amounts[-1])

        if index + 1 < len(lines):
            return parse_money(lines[index + 1])

        return None

    return None


def _parse_dates(lines, date_order):
    invoice_date = None
    due_date = None
    warnings = []

    for line in lines:
        invoice_match = re.search(r"Invoice Date:\s*(.+)", line, re.IGNORECASE)
        if invoice_match:
            raw = invoice_match.group(1).strip()
            invoice_date, ambiguous = normalize_date(raw, date_order)
            if ambiguous:
                warnings.append(
                    f"Ambiguous invoice date '{raw}' read as MDY"
                )

        due_match = re.search(r"Due Date:\s*(.+)", line, re.IGNORECASE)
        if due_match:
            raw = due_match.group(1).strip()
            due_date, ambiguous = normalize_date(raw, date_order)
            if ambiguous:
                warnings.append(f"Ambiguous due date '{raw}' read as MDY")

    if invoice_date is not None and due_date is not None:
        return invoice_date, due_date, warnings

    # Fallback for layouts where dates sit alone on their own lines.
    standalone = []
    for line in lines:
        parsed, ambiguous = normalize_date(line, date_order)
        if parsed is not None:
            standalone.append((parsed, ambiguous, line))

    if invoice_date is None and standalone:
        invoice_date, ambiguous, raw = standalone[0]
        if ambiguous:
            warnings.append(f"Ambiguous invoice date '{raw}' read as MDY")

    if due_date is None and len(standalone) >= 2:
        due_date, ambiguous, raw = standalone[1]
        if ambiguous:
            warnings.append(f"Ambiguous due date '{raw}' read as MDY")

    return invoice_date, due_date, warnings


def parse_invoice(text, date_order=None):
    """Parse invoice text into a field dictionary.

    date_order declares how a numeric date such as 03/04/2026 should be read
    when the value alone cannot settle it. Left unset, such a date is parsed as
    MDY for display and flagged for review rather than passed off as certain.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    invoice_date, due_date, warnings = _parse_dates(lines, date_order)

    return {
        "vendor": _find_vendor(lines),
        "invoice_number": _find_invoice_number(lines),
        "invoice_date": invoice_date,
        "due_date": due_date,
        "customer": _find_customer(lines),
        "subtotal": _find_money(lines, ["Subtotal:", "Net Amount"]),
        "tax": _find_tax(lines),
        "total": _find_money(lines, ["Total:", "Amount Due"]),
        "currency": detect_currency(lines),
        "parse_warnings": warnings,
    }
