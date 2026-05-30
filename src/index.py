#!/usr/bin/env python3
"""
bank-statement-normalizer — any bank export → standard normalized transaction schema
Supports: PDF statements, CSV exports, Excel files from any bank in any country
"""
import anthropic
import base64
import csv
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional


SYSTEM = """You are an expert financial data normalizer.
Convert bank statement data into a standard normalized JSON format.

Rules:
- Dates must be YYYY-MM-DD format
- Amounts: positive = credit/money-in, negative = debit/money-out
- Normalize merchant names (remove transaction codes, normalize casing)
- Categorize each transaction from this list:
  groceries, dining, transport, fuel, utilities, rent, salary, transfer,
  shopping, entertainment, healthcare, education, insurance, investment,
  atm_withdrawal, bank_fee, refund, subscription, travel, other

Return ONLY valid JSON — no markdown, no explanation.

Format:
{
  "bank_name": "string or null",
  "account_holder": "string or null",
  "account_number_last4": "string or null",
  "currency": "USD|GBP|EUR|EGP|...",
  "statement_period": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" },
  "opening_balance": number or null,
  "closing_balance": number or null,
  "total_credits": number,
  "total_debits": number,
  "transaction_count": number,
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "normalized merchant/description",
      "raw_description": "original text",
      "amount": number,
      "balance_after": number or null,
      "category": "groceries|dining|...",
      "reference": "string or null",
      "is_recurring": true or false
    }
  ],
  "detected_format": "pdf|csv|excel|text",
  "source_bank_country": "string or null",
  "confidence": 0.0
}"""


def read_file(path: Path) -> tuple[str, str, str]:
    """Returns (content_type, content, format)"""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        return "pdf_base64", data, "pdf"

    if suffix in (".csv", ".txt"):
        return "text", path.read_text(encoding="utf-8", errors="replace"), "csv"

    if suffix in (".xls", ".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = []
            for row in ws.iter_rows(values_only=True):
                rows.append(",".join(str(c) if c is not None else "" for c in row))
            return "text", "\n".join(rows), "excel"
        except ImportError:
            return "text", path.read_text(errors="replace"), "excel"

    return "text", path.read_text(encoding="utf-8", errors="replace"), "text"


def normalize(file_path: str) -> dict:
    client = anthropic.Anthropic()
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Not found: {file_path}")

    content_type, content, fmt = read_file(path)

    if content_type == "pdf_base64":
        messages = [{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": content}},
                {"type": "text", "text": "Normalize all transactions from this bank statement."}
            ]
        }]
    else:
        # Truncate very large files
        if len(content) > 40000:
            content = content[:40000] + "\n[truncated]"
        messages = [{
            "role": "user",
            "content": f"Normalize all transactions from this bank statement ({fmt} format):\n\n{content}"
        }]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM,
        messages=messages
    )

    text = response.content[0].text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    return json.loads(text)


def to_csv(result: dict, output_path: str):
    """Export normalized transactions to CSV."""
    txns = result.get("transactions", [])
    if not txns:
        print("No transactions found")
        return
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","description","raw_description","amount","balance_after","category","reference","is_recurring"])
        writer.writeheader()
        writer.writerows(txns)
    print(f"Exported {len(txns)} transactions to {output_path}")


def print_summary(result: dict):
    txns = result.get("transactions", [])
    print(f"\n{'─'*55}")
    print(f"  Bank Statement Normalized")
    print(f"{'─'*55}")
    print(f"  Bank:          {result.get('bank_name', 'Unknown')}")
    print(f"  Account:       ****{result.get('account_number_last4', '????')}")
    print(f"  Currency:      {result.get('currency', '?')}")
    p = result.get("statement_period", {})
    print(f"  Period:        {p.get('from','?')} → {p.get('to','?')}")
    print(f"  Transactions:  {result.get('transaction_count', len(txns))}")
    print(f"  Total credits: {result.get('currency','')}{result.get('total_credits',0):,.2f}")
    print(f"  Total debits:  {result.get('currency','')}{abs(result.get('total_debits',0)):,.2f}")
    print(f"  Closing bal:   {result.get('currency','')}{result.get('closing_balance',0):,.2f}")
    print()
    # Category breakdown
    cats: dict = {}
    for t in txns:
        c = t.get("category","other")
        cats[c] = cats.get(c, 0) + 1
    if cats:
        print("  Categories:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1])[:8]:
            print(f"    {cat:<20} {count} txns")
    print(f"\n  Confidence: {int(result.get('confidence',0)*100)}%")
    print(f"{'─'*55}\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m bank_statement_normalizer <statement.pdf|.csv|.xlsx> [--json] [--csv output.csv]")
        sys.exit(0)

    result = normalize(args[0])

    csv_idx = args.index("--csv") if "--csv" in args else -1
    if csv_idx >= 0 and args[csv_idx + 1]:
        to_csv(result, args[csv_idx + 1])
    elif "--json" in args:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_summary(result)
