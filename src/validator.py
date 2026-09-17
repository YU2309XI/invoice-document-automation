"""Validate extracted invoice data and decide whether it needs human review."""

REQUIRED_FIELDS = [
    "vendor",
    "invoice_number",
    "invoice_date",
    "customer",
    "total",
    "currency",
]

# Tax rounding routinely produces a one-cent difference, so that much is
# tolerated. Comparison happens in whole cents: comparing floats directly puts
# an exactly-one-cent gap on the wrong side of the threshold, because
# abs(108.00 - 108.01) evaluates to 0.010000000000005116.
TOTAL_TOLERANCE_CENTS = 1


def validate_invoice(invoice):
    """Return (status, issues).

    An invoice is only marked OK when every required field was found, the
    arithmetic holds, and the parser did not have to guess at anything.
    """
    issues = []

    for field in REQUIRED_FIELDS:
        if invoice.get(field) is None:
            issues.append(f"Missing required field: {field}")

    subtotal = invoice.get("subtotal")
    tax = invoice.get("tax")
    total = invoice.get("total")

    if subtotal is not None and tax is not None and total is not None:
        expected_cents = round((subtotal + tax) * 100)
        actual_cents = round(total * 100)

        if abs(expected_cents - actual_cents) > TOTAL_TOLERANCE_CENTS:
            issues.append(
                f"Total mismatch: expected {expected_cents / 100:.2f}, "
                f"found {actual_cents / 100:.2f}"
            )

    # A value the parser could not settle on is treated as an issue, not as a
    # result. A wrong date that looks right is worse than one that is queried.
    issues.extend(invoice.get("parse_warnings") or [])

    status = "NEEDS REVIEW" if issues else "OK"

    return status, issues
