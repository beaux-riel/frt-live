#!/usr/bin/env python3
"""
FRT Parser Testing and Diagnostics
Tests different extraction approaches on FRT PDF pages
"""

import pdfplumber
import json
import logging
from pathlib import Path
from page_classifier import PageClassifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_page_classification(pdf_path: str, max_pages: int = 20):
    """
    Test page classification on first N pages
    """
    logger.info(f"Testing page classification on {pdf_path}")

    classifier = PageClassifier()

    with pdfplumber.open(pdf_path) as pdf:
        print(f"\nTotal pages in PDF: {len(pdf.pages)}\n")
        print("=" * 80)
        print(f"{'Page':<6} {'Type':<12} {'Words':<8} {'Columns':<10} {'Rows':<6} {'Details'}")
        print("=" * 80)

        for i in range(min(max_pages, len(pdf.pages))):
            page = pdf.pages[i]
            page_type = classifier.classify(page)

            # Get metrics for details
            metrics = classifier._extract_metrics(page)

            # Show first 50 chars of text for context
            all_text = metrics.get('all_text', '')
            text_preview = all_text[:50] + "..." if len(all_text) > 50 else all_text

            print(f"{i+1:<6} {page_type:<12} {metrics['word_count']:<8} {metrics['num_columns']:<10} {metrics['row_count']:<6} {text_preview}")

            # For REPORT pages, show what keywords triggered it
            if page_type == 'REPORT':
                if metrics['has_report_keywords']:
                    print(f"       └─ Has report keywords")
                if metrics['has_section_headers']:
                    print(f"       └─ Has section headers")

        print("=" * 80)


def test_extraction_methods(pdf_path: str, page_num: int = 5):
    """
    Compare different extraction methods on a specific page
    """
    logger.info(f"Testing extraction methods on page {page_num}")

    with pdfplumber.open(pdf_path) as pdf:
        if page_num > len(pdf.pages):
            logger.error(f"Page {page_num} doesn't exist")
            return

        page = pdf.pages[page_num - 1]

        print(f"\n{'='*80}")
        print(f"PAGE {page_num} EXTRACTION COMPARISON")
        print(f"{'='*80}\n")

        # Method 1: Extract tables using pdfplumber's built-in method
        print("METHOD 1: pdfplumber extract_tables()")
        print("-" * 80)
        tables = page.extract_tables()
        if tables:
            for tidx, table in enumerate(tables):
                print(f"\nTable {tidx + 1}:")
                for ridx, row in enumerate(table[:5]):  # First 5 rows
                    print(f"  Row {ridx}: {row[:4]}")  # First 4 columns
        else:
            print("No tables detected")

        # Method 2: Extract text
        print(f"\n\nMETHOD 2: extract_text()")
        print("-" * 80)
        text = page.extract_text()
        print(text[:500] if text else "No text extracted")

        # Method 3: Extract words with positions
        print(f"\n\nMETHOD 3: extract_words() - Column-based approach")
        print("-" * 80)
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if words:
            print(f"Total words: {len(words)}")
            print(f"First 10 words:")
            for w in words[:10]:
                print(f"  '{w['text']}' at x={w['x0']:.1f}, y={w['top']:.1f}")
        else:
            print("No words extracted")

        # Method 4: Check page type
        print(f"\n\nPAGE CLASSIFICATION")
        print("-" * 80)
        classifier = PageClassifier()
        page_type = classifier.classify(page)
        metrics = classifier._extract_metrics(page)
        print(f"Classified as: {page_type}")
        print(f"Metrics:")
        for key, value in metrics.items():
            if key != 'all_text':
                print(f"  {key}: {value}")


def extract_single_page_structured(pdf_path: str, page_num: int):
    """
    Extract a single page using the table extraction method
    """
    logger.info(f"Extracting page {page_num} with table method")

    with pdfplumber.open(pdf_path) as pdf:
        if page_num > len(pdf.pages):
            logger.error(f"Page {page_num} doesn't exist")
            return None

        page = pdf.pages[page_num - 1]

        # Classify page
        classifier = PageClassifier()
        page_type = classifier.classify(page)

        print(f"\nPage {page_num} Type: {page_type}")
        print("=" * 80)

        if page_type == 'REPORT':
            print("This is a REPORT page - skipping table extraction")
            return None

        # Try table extraction
        tables = page.extract_tables(table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "explicit_vertical_lines": [],
            "explicit_horizontal_lines": [],
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 3,
            "min_words_horizontal": 1,
            "intersection_tolerance": 3
        })

        if not tables:
            print("No tables extracted")
            return None

        print(f"Extracted {len(tables)} table(s)")

        # Display first table
        if tables:
            table = tables[0]
            print(f"\nFirst table has {len(table)} rows")
            print("\nFirst 5 rows:")
            for i, row in enumerate(table[:5]):
                print(f"{i}: {row}")

        return tables


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Test FRT PDF extraction methods')
    parser.add_argument('pdf_path', help='Path to FRT PDF file')
    parser.add_argument('--classify', action='store_true', help='Test page classification')
    parser.add_argument('--compare', type=int, metavar='PAGE', help='Compare extraction methods on specific page')
    parser.add_argument('--extract', type=int, metavar='PAGE', help='Extract specific page with table method')
    parser.add_argument('--max-pages', type=int, default=20, help='Maximum pages to classify (default: 20)')

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return

    if args.classify:
        test_page_classification(str(pdf_path), args.max_pages)
    elif args.compare:
        test_extraction_methods(str(pdf_path), args.compare)
    elif args.extract:
        extract_single_page_structured(str(pdf_path), args.extract)
    else:
        # Run all tests
        print("\n" + "=" * 80)
        print("RUNNING ALL DIAGNOSTIC TESTS")
        print("=" * 80)

        test_page_classification(str(pdf_path), args.max_pages)

        print("\n\nTesting extraction on page 5 (should be TABLE)...")
        test_extraction_methods(str(pdf_path), 5)

        print("\n\nTesting extraction on page 3 (should be REPORT)...")
        test_extraction_methods(str(pdf_path), 3)


if __name__ == '__main__':
    main()
