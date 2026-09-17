"""Turn a folder of invoice PDFs into a validated Excel report.

Usage:
    python src/main.py
    python src/main.py --input data/invoices --output output/invoice_report.xlsx
    python src/main.py --date-order DMY
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from extractor import extract_text_from_pdf
from invoice_parser import parse_invoice
from validator import validate_invoice
from style_report import style_report

DEFAULT_INPUT = Path("data/invoices")
DEFAULT_OUTPUT = Path("output/invoice_report.xlsx")

COLUMN_ORDER = [
    "source_file",
    "extraction_method",
    "vendor",
    "invoice_number",
    "invoice_date",
    "due_date",
    "customer",
    "currency",
    "subtotal",
    "tax",
    "total",
    "status",
    "issues",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract invoice data from PDFs into a validated Excel report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="folder containing invoice PDFs")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Excel file to write")
    parser.add_argument("--date-order", choices=["MDY", "DMY"], default=None,
                        help="declare how numeric dates are written on these "
                             "invoices; left unset, an ambiguous date such as "
                             "03/04/2026 is flagged for review instead of guessed")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress per-invoice progress output")
    return parser.parse_args(argv)


def process_invoice(pdf_path, date_order):
    text, extraction_method = extract_text_from_pdf(pdf_path)

    invoice = parse_invoice(text, date_order=date_order)
    invoice["source_file"] = pdf_path.name
    invoice["extraction_method"] = extraction_method

    status, issues = validate_invoice(invoice)
    invoice["status"] = status
    invoice["issues"] = "; ".join(issues)

    # The warning list has served its purpose inside validate_invoice and
    # would not survive the trip into a spreadsheet cell.
    invoice.pop("parse_warnings", None)

    return invoice


def build_summary(frame):
    currency_totals = (
        frame[frame["currency"].notna()]
        .groupby("currency")["total"]
        .sum()
        .to_dict()
    )

    rows = [
        ["INVOICE PROCESSING SUMMARY", ""],
        ["", ""],
        ["Processing Overview", ""],
        ["Total Invoices", len(frame)],
        ["Successfully Processed", int((frame["status"] == "OK").sum())],
        ["Needs Review", int((frame["status"] == "NEEDS REVIEW").sum())],
        ["", ""],
        ["Extraction Methods", ""],
        ["Text PDFs", int((frame["extraction_method"] == "TEXT").sum())],
        ["OCR / Scanned PDFs", int((frame["extraction_method"] == "OCR").sum())],
        ["", ""],
        ["Invoice Value by Currency", ""],
    ]

    for currency, value in sorted(currency_totals.items()):
        rows.append([f"{currency} Invoice Value", value])

    return pd.DataFrame(rows, columns=["Metric", "Value"])


def write_report(output_path, summary, frame, review):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="Summary")
        frame.to_excel(writer, index=False, sheet_name="Invoices")
        review.to_excel(writer, index=False, sheet_name="Needs Review")

    style_report(output_path)


def run(args):
    pdf_files = sorted(args.input.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {args.input}")

    invoices = []
    for pdf_path in pdf_files:
        if not args.quiet:
            print(f"Processing: {pdf_path.name}")

        invoice = process_invoice(pdf_path, args.date_order)
        invoices.append(invoice)

        if not args.quiet:
            print(f"  {invoice['extraction_method']}  {invoice['status']}")

    frame = pd.DataFrame(invoices)[COLUMN_ORDER]
    review = frame[frame["status"] == "NEEDS REVIEW"]

    write_report(args.output, build_summary(frame), frame, review)

    return frame


def main(argv=None):
    args = parse_args(argv)

    try:
        frame = run(args)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        ok = int((frame["status"] == "OK").sum())
        review = int((frame["status"] == "NEEDS REVIEW").sum())
        print(f"\n{len(frame)} invoices processed, {ok} clean, {review} need review")
        print(f"Report written to    {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
