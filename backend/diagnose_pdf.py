#!/usr/bin/env python3
"""
Diagnostic script to inspect PDF structure
"""

import pdfplumber
from pathlib import Path

pdf_path = Path('data/frt_current.pdf')

if not pdf_path.exists():
    print(f"ERROR: PDF not found at {pdf_path}")
    exit(1)

print(f"Opening PDF: {pdf_path}")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print()

    # Inspect first few pages
    for page_num in range(min(3, len(pdf.pages))):
        page = pdf.pages[page_num]
        print(f"\n{'='*80}")
        print(f"PAGE {page_num + 1}")
        print(f"{'='*80}")
        print(f"Page dimensions: {page.width} x {page.height}")
        print()

        # Extract all text
        text = page.extract_text()
        print("Full text (first 500 chars):")
        print("-" * 80)
        print(text[:500] if text else "(No text found)")
        print("-" * 80)
        print()

        # Extract words with positions
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        print(f"Total words found: {len(words)}")
        print()
        print("First 20 words with positions:")
        print("-" * 80)
        for i, word in enumerate(words[:20]):
            print(f"{i+1:3d}. '{word['text']}' @ x:{word['x0']:.1f}-{word['x1']:.1f}, y:{word['top']:.1f}-{word['bottom']:.1f}")
        print("-" * 80)
        print()

        # Look for potential column headers
        potential_headers = ['FRN', 'MAKE', 'MODEL', 'MANUFACTURER', 'TYPE', 'ACTION', 'CLASS', 'NOTES']
        print("Searching for potential column headers:")
        print("-" * 80)
        found_headers = []
        for word in words:
            word_upper = word['text'].upper()
            for header in potential_headers:
                if header in word_upper or word_upper in header:
                    found_headers.append(word)
                    print(f"Found '{word['text']}' @ x:{word['x0']:.1f}-{word['x1']:.1f}, y:{word['top']:.1f}-{word['bottom']:.1f}")
        print(f"Total potential headers found: {len(found_headers)}")
        print("-" * 80)
        print()

        # Extract tables
        tables = page.extract_tables()
        print(f"Tables found: {len(tables)}")
        if tables:
            for idx, table in enumerate(tables[:2]):  # Show first 2 tables
                print(f"\nTable {idx + 1}:")
                print(f"  Rows: {len(table)}")
                print(f"  First row (header?): {table[0] if table else 'N/A'}")
                if len(table) > 1:
                    print(f"  Second row: {table[1]}")
        print()
