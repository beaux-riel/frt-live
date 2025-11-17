#!/usr/bin/env python3
"""Quick diagnostic to check PDF structure"""
import pdfplumber
from pathlib import Path

pdf_path = Path('data/frt_current.pdf')
print(f"Opening {pdf_path}")

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages reported: {len(pdf.pages)}")
    print(f"\nChecking first few pages:")

    for i in range(min(5, len(pdf.pages))):
        page = pdf.pages[i]
        text = page.extract_text()
        tables = page.extract_tables()
        words = page.extract_words()

        print(f"\nPage {i+1}:")
        print(f"  Text length: {len(text) if text else 0}")
        print(f"  Tables found: {len(tables)}")
        print(f"  Words found: {len(words)}")
        print(f"  First 100 chars of text: {text[:100] if text else 'None'}")
