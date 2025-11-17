#!/usr/bin/env python3
"""
Validation script for FRN 152726 multipage extraction

This script specifically tests the extraction of FRN 152726,
which spans 3 pages in the PDF.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frt_report_parser import FRTReportParser
from page_classifier import PageClassifier
import pdfplumber


def main():
    """Run validation for FRN 152726"""
    print("=" * 70)
    print("FRN 152726 Multipage Extraction Validation")
    print("=" * 70)

    # Setup
    data_dir = Path(__file__).parent.parent / 'data'
    pdf_path = data_dir / 'frt_current.pdf'

    if not pdf_path.exists():
        print(f"❌ ERROR: Test PDF not found at {pdf_path}")
        print("   Please ensure frt_current.pdf exists in the data directory")
        return 1

    print(f"\n📄 PDF Path: {pdf_path}")

    # Initialize parsers
    report_parser = FRTReportParser()
    classifier = PageClassifier()

    # Open PDF and find FRN 152726 pages
    print("\n🔍 Searching for FRN 152726 pages...")

    frn_152726_pages = []
    frn_page_numbers = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and '152726' in text:
                frn_152726_pages.append(page)
                frn_page_numbers.append(page_num)

                # Classify page
                page_type = classifier.classify(page)
                print(f"   Found FRN 152726 on page {page_num} (type: {page_type})")

                # Stop after finding 3 consecutive pages
                if len(frn_152726_pages) >= 3:
                    # Check if there are more pages
                    if page_num < len(pdf.pages):
                        next_page = pdf.pages[page_num]
                        next_text = next_page.extract_text()
                        if '152726' in next_text:
                            continue  # Keep going
                        else:
                            break  # Done
                    else:
                        break

    if not frn_152726_pages:
        print("❌ ERROR: Could not find FRN 152726 in PDF")
        return 1

    print(f"\n✅ Found {len(frn_152726_pages)} page(s) for FRN 152726:")
    print(f"   Page numbers: {frn_page_numbers}")

    # Parse the multipage report
    print("\n🔄 Parsing multipage report...")

    record = report_parser.parse_multi_page_report(frn_152726_pages)

    if not record:
        print("❌ ERROR: Parser returned None")
        return 1

    # Validate results
    print("\n" + "=" * 70)
    print("EXTRACTION RESULTS")
    print("=" * 70)

    # Basic fields
    print(f"\n📋 Basic Information:")
    print(f"   FRN: {record.get('frn', 'MISSING')}")
    print(f"   Make: {record.get('make', 'MISSING')}")
    print(f"   Model: {record.get('model', 'MISSING')}")
    print(f"   Manufacturer: {record.get('manufacturer', 'MISSING')}")
    print(f"   Type: {record.get('type', 'MISSING')}")
    print(f"   Action: {record.get('action', 'MISSING')}")
    print(f"   Class: {record.get('class', 'MISSING')}")
    print(f"   Country: {record.get('country', 'MISSING')}")
    print(f"   Level: {record.get('level', 'MISSING')}")

    # Multipage metadata
    print(f"\n📊 Multipage Metadata:")
    print(f"   Multipage: {record.get('multipage', False)}")
    print(f"   Page Count: {record.get('page_count', 1)}")

    # Content metrics
    notes_length = len(record.get('notes', ''))
    product_codes_count = len(record.get('product_codes', []))
    calibre_variants_count = len(record.get('calibre_variants', []))

    print(f"\n📝 Content Metrics:")
    print(f"   Notes Length: {notes_length} characters")
    print(f"   Product Codes: {product_codes_count} codes")
    print(f"   Calibre Variants: {calibre_variants_count} variants")
    print(f"   Cross References: {record.get('cross_references', 'MISSING')}")

    # Show sample content
    if record.get('notes'):
        print(f"\n📄 Notes Preview (first 300 chars):")
        print(f"   {record['notes'][:300]}...")

    if record.get('product_codes'):
        print(f"\n🏷️  Product Codes (first 10):")
        for code in record['product_codes'][:10]:
            print(f"   - {code}")

    # Validation checks
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)

    checks_passed = 0
    checks_total = 0

    # Check 1: FRN correct
    checks_total += 1
    if record.get('frn') == '152726':
        print("✅ FRN is correct (152726)")
        checks_passed += 1
    else:
        print(f"❌ FRN is incorrect: {record.get('frn')} (expected 152726)")

    # Check 2: Make
    checks_total += 1
    if record.get('make') == '2 Vets Arms':
        print("✅ Make is correct (2 Vets Arms)")
        checks_passed += 1
    else:
        print(f"❌ Make is incorrect: {record.get('make')} (expected 2 Vets Arms)")

    # Check 3: Model
    checks_total += 1
    if record.get('model') == '2VA-15':
        print("✅ Model is correct (2VA-15)")
        checks_passed += 1
    else:
        print(f"❌ Model is incorrect: {record.get('model')} (expected 2VA-15)")

    # Check 4: Multipage
    checks_total += 1
    if len(frn_152726_pages) > 1:
        if record.get('multipage') is True:
            print(f"✅ Multipage flag is set correctly")
            checks_passed += 1
        else:
            print(f"❌ Multipage flag should be True for {len(frn_152726_pages)} pages")

    # Check 5: Notes length
    checks_total += 1
    if notes_length > 100:
        print(f"✅ Notes have substantial content ({notes_length} chars)")
        checks_passed += 1
    else:
        print(f"❌ Notes are too short ({notes_length} chars), likely missing continuation data")

    # Check 6: Expected keywords in notes
    checks_total += 1
    expected_keywords = ['2VA-15', 'AR-15', 'receiver', 'magazine']
    found_keywords = [kw for kw in expected_keywords if kw.lower() in record.get('notes', '').lower()]
    if len(found_keywords) >= 3:
        print(f"✅ Notes contain expected keywords ({len(found_keywords)}/{len(expected_keywords)})")
        checks_passed += 1
    else:
        print(f"❌ Notes missing expected keywords (found {len(found_keywords)}/{len(expected_keywords)})")

    # Check 7: Product codes (if 3 pages)
    if len(frn_152726_pages) >= 3:
        checks_total += 1
        if product_codes_count > 0:
            print(f"✅ Product codes extracted ({product_codes_count} codes)")
            checks_passed += 1
        else:
            print(f"❌ No product codes extracted (expected from page 3)")

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    success_rate = (checks_passed / checks_total * 100) if checks_total > 0 else 0

    print(f"\n   Checks Passed: {checks_passed}/{checks_total} ({success_rate:.1f}%)")

    if checks_passed == checks_total:
        print("\n   🎉 ALL CHECKS PASSED! Multipage extraction is working correctly.")
        return_code = 0
    elif success_rate >= 80:
        print("\n   ⚠️  MOST CHECKS PASSED. Minor issues detected.")
        return_code = 0
    else:
        print("\n   ❌ VALIDATION FAILED. Significant issues detected.")
        return_code = 1

    # Save extracted record for inspection
    output_path = data_dir / 'frn_152726_extracted.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Full record saved to: {output_path}")

    return return_code


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
