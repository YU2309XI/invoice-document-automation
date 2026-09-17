import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from invoice_parser import (  # noqa: E402
    detect_currency,
    normalize_date,
    parse_invoice,
    parse_money,
)
from validator import validate_invoice  # noqa: E402

USD_INVOICE = """INVOICE
Harbour Supply Co
Invoice #: INV-4001
Invoice Date: September 10, 2026
Due Date: October 10, 2026
Bill To
Acme Ltd
Subtotal: $500.00
Tax 8%: $40.00
Total: $540.00"""


# --- dates ---------------------------------------------------------------

def test_textual_date_is_unambiguous():
    assert normalize_date("September 10, 2026") == ("2026-09-10", False)


def test_day_over_twelve_settles_the_order_itself():
    """15 cannot be a month, so 09/15/2026 needs no convention to read."""
    assert normalize_date("09/15/2026") == ("2026-09-15", False)


def test_day_first_when_first_component_exceeds_twelve():
    assert normalize_date("15/09/2026") == ("2026-09-15", False)


def test_genuinely_ambiguous_date_is_flagged():
    """03/04/2026 is 3 April in Europe and 4 March in the US."""
    iso, ambiguous = normalize_date("03/04/2026")
    assert ambiguous is True
    assert iso == "2026-03-04"


def test_declared_order_resolves_the_ambiguity():
    assert normalize_date("03/04/2026", date_order="DMY") == ("2026-04-03", False)
    assert normalize_date("03/04/2026", date_order="MDY") == ("2026-03-04", False)


def test_identical_components_are_not_ambiguous():
    """05/05/2026 reads the same under either convention."""
    assert normalize_date("05/05/2026") == ("2026-05-05", False)


def test_impossible_date_returns_none():
    assert normalize_date("13/13/2026") == (None, False)
    assert normalize_date("02/30/2026") == (None, False)


def test_unparseable_date_returns_none():
    assert normalize_date("not a date") == (None, False)


# --- currency ------------------------------------------------------------

@pytest.mark.parametrize(
    "line,expected",
    [
        ("Total: $540.00", "USD"),
        ("Total: USD 540.00", "USD"),
        ("Total: €456.00", "EUR"),
        ("Total: EUR 456.00", "EUR"),
        ("Total: £320.00", "GBP"),
        ("Total: GBP 320.00", "GBP"),
    ],
)
def test_currency_symbols_and_codes(line, expected):
    assert detect_currency([line]) == expected


def test_currency_is_none_when_absent():
    assert detect_currency(["Total: 540.00"]) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("$1,234.56", 1234.56),
        ("€456.00", 456.0),
        ("£320.50", 320.5),
        ("EUR 456.00", 456.0),
        ("nonsense", None),
    ],
)
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


# --- field extraction ----------------------------------------------------

def test_parses_a_clean_invoice():
    invoice = parse_invoice(USD_INVOICE)
    assert invoice["vendor"] == "Harbour Supply Co"
    assert invoice["invoice_number"] == "INV-4001"
    assert invoice["invoice_date"] == "2026-09-10"
    assert invoice["due_date"] == "2026-10-10"
    assert invoice["customer"] == "Acme Ltd"
    assert invoice["currency"] == "USD"
    assert invoice["subtotal"] == 500.0
    assert invoice["tax"] == 40.0
    assert invoice["total"] == 540.0
    assert invoice["parse_warnings"] == []


def test_invoice_number_from_a_label_format():
    """Not every invoice number looks like INV-1234."""
    text = USD_INVOICE.replace("Invoice #: INV-4001", "Invoice No. 2026/0042")
    assert parse_invoice(text)["invoice_number"] == "2026/0042"


def test_tax_line_with_percentage_takes_the_amount():
    """'Tax 8%: $40.00' must yield 40.00, not 8."""
    assert parse_invoice(USD_INVOICE)["tax"] == 40.0


def test_european_invoice_parses_fully():
    text = """INVOICE
Nordkap Outdoor AB
Invoice #: INV-9001
Invoice Date: 03/04/2026
Bill To
Acme Ltd
Subtotal: EUR 100.00
VAT 25%: EUR 25.00
Total: EUR 125.00"""
    invoice = parse_invoice(text, date_order="DMY")
    assert invoice["currency"] == "EUR"
    assert invoice["total"] == 125.0
    assert invoice["tax"] == 25.0
    assert invoice["invoice_date"] == "2026-04-03"


def test_gbp_invoice_parses_fully():
    text = USD_INVOICE.replace("$", "£")
    invoice = parse_invoice(text)
    assert invoice["currency"] == "GBP"
    assert invoice["total"] == 540.0


# --- validation ----------------------------------------------------------

def test_clean_invoice_passes():
    status, issues = validate_invoice(parse_invoice(USD_INVOICE))
    assert status == "OK"
    assert issues == []


def test_missing_required_field_is_flagged():
    text = USD_INVOICE.replace("Invoice #: INV-4001", "")
    status, issues = validate_invoice(parse_invoice(text))
    assert status == "NEEDS REVIEW"
    assert any("invoice_number" in issue for issue in issues)


def test_total_mismatch_is_flagged():
    text = USD_INVOICE.replace("Total: $540.00", "Total: $590.00")
    status, issues = validate_invoice(parse_invoice(text))
    assert status == "NEEDS REVIEW"
    assert any("Total mismatch" in issue for issue in issues)


def test_arithmetic_within_a_cent_passes():
    """Rounding noise is not a discrepancy."""
    invoice = {
        "vendor": "v", "invoice_number": "1", "invoice_date": "2026-01-01",
        "customer": "c", "currency": "USD",
        "subtotal": 100.0, "tax": 8.005, "total": 108.01,
        "parse_warnings": [],
    }
    assert validate_invoice(invoice)[0] == "OK"


def test_ambiguous_date_routes_to_review():
    """The point of the whole design: a plausible guess is still a guess."""
    text = USD_INVOICE.replace("Invoice Date: September 10, 2026",
                               "Invoice Date: 03/04/2026")
    status, issues = validate_invoice(parse_invoice(text))
    assert status == "NEEDS REVIEW"
    assert any("Ambiguous" in issue for issue in issues)


def test_declared_date_order_keeps_the_invoice_clean():
    text = USD_INVOICE.replace("Invoice Date: September 10, 2026",
                               "Invoice Date: 03/04/2026")
    status, _ = validate_invoice(parse_invoice(text, date_order="MDY"))
    assert status == "OK"
