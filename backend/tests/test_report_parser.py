#!/usr/bin/env python3
"""
Test script for FRT Report Parser
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pdfplumber
from frt_report_parser import FRTReportParser


def test_single_page(pdf_path: str, page_num: int):
    """Test parsing a single report page"""
    print(f"\n{'='*80}")
    print(f"Testing Report Parser on Page {page_num}")
    print(f"{'='*80}\n")

    parser = FRTReportParser()

    with pdfplumber.open(pdf_path) as pdf:
        if page_num > len(pdf.pages):
            print(f"Error: Page {page_num} doesn't exist")
            return

        page = pdf.pages[page_num - 1]

        # Parse the page
        result = parser.parse_report_page(page)

        if result:
            print("✓ Successfully parsed report page\n")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("✗ Failed to parse report page")
            print("\nRaw text extract:")
            print(page.extract_text()[:500])


def test_multiple_pages(pdf_path: str, page_nums: list):
    """Test parsing multiple report pages"""
    print(f"\n{'='*80}")
    print(f"Testing Report Parser on Pages {page_nums}")
    print(f"{'='*80}\n")

    parser = FRTReportParser()
    results = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in page_nums:
            if page_num > len(pdf.pages):
                print(f"Skipping page {page_num} (doesn't exist)")
                continue

            page = pdf.pages[page_num - 1]
            result = parser.parse_report_page(page)

            if result:
                results.append(result)
                print(f"✓ Page {page_num}: FRN={result['frn']}, Make={result['make']}, Model={result['model']}")
            else:
                print(f"✗ Page {page_num}: Failed to parse")

    print(f"\nSuccessfully parsed {len(results)}/{len(page_nums)} pages")

    if results:
        output_file = Path(__file__).parent.parent / 'data' / 'test_report_extraction.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_file}")


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Test FRT Report Parser')
    parser.add_argument('pdf_path', help='Path to FRT PDF file')
    parser.add_argument('--page', type=int, help='Test single page')
    parser.add_argument('--pages', type=int, nargs='+', help='Test multiple pages')
    parser.add_argument('--range', type=str, help='Test page range (e.g., 3-10)')

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        return 1

    if args.page:
        test_single_page(str(pdf_path), args.page)
    elif args.pages:
        test_multiple_pages(str(pdf_path), args.pages)
    elif args.range:
        # Parse range like "3-10"
        start, end = map(int, args.range.split('-'))
        pages = list(range(start, end + 1))
        test_multiple_pages(str(pdf_path), pages)
    else:
        # Default: test a few sample pages
        print("No pages specified. Testing sample pages...")
        test_multiple_pages(str(pdf_path), [3, 5, 7, 10, 501, 1000])

    return 0


if __name__ == '__main__':
    sys.exit(main())
