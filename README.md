# bank-statement-normalizer

> **Any bank statement → standard normalized transaction schema.** Supports PDF statements, CSV exports, Excel files from any bank in any country. Auto-categorizes transactions.

[![PyPI](https://img.shields.io/pypi/v/bank-statement-normalizer?style=flat)](https://pypi.org/project/bank-statement-normalizer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quickstart

```bash
pip install bank-statement-normalizer
python -m bank_statement_normalizer statement.pdf
python -m bank_statement_normalizer statement.csv --csv normalized.csv
```

## Output format

Every transaction normalized to:

```json
{
  "date": "2025-05-01",
  "description": "Amazon UK",
  "raw_description": "AMAZON.CO.UK*2A3B4C AMZN.COM/BILL GB",
  "amount": -42.99,
  "balance_after": 1842.10,
  "category": "shopping",
  "reference": "TXN-001",
  "is_recurring": false
}
```

## Supported inputs

| Format | Examples |
|--------|---------|
| PDF | Bank of Cairo, HSBC, Barclays, Chase, any bank |
| CSV | Monzo, Starling, Revolut, most banks |
| Excel | Older bank exports, accounting tools |

## License
MIT © [Alper Nabil Gabra Zakher](https://github.com/AlperNab)
