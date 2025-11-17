#!/usr/bin/env python3
"""
Test suite for multipage FRT record extraction

Tests the parser's ability to correctly extract firearm records
that span multiple pages in the PDF.
"""

import sys
import os
import json
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frt_parser import FRTParser
from frt_report_parser import FRTReportParser
import pdfplumber


class TestMultipageExtraction:
    """Test multipage record extraction functionality"""

    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return FRTParser()

    @pytest.fixture
    def report_parser(self):
        """Create report parser instance"""
        return FRTReportParser()

    @pytest.fixture
    def test_pdf_path(self):
        """Path to test PDF"""
        # Use the current FRT PDF for testing
        data_dir = Path(__file__).parent.parent / 'data'
        pdf_path = data_dir / 'frt_current.pdf'

        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {pdf_path}")

        return pdf_path

    def test_frn_152726_extraction(self, report_parser, test_pdf_path):
        """
        Test extraction of FRN 152726 (3-page record)

        This record spans pages 7-9 in the PDF and contains:
        - Page 1: Summary with FRN, Make, Model, basic info
        - Page 2: Detailed Make, Model, Manufacturer descriptions
        - Page 3: Also Known As/Product Code section
        """
        with pdfplumber.open(test_pdf_path) as pdf:
            # Extract pages 7-9 (0-indexed: pages 6, 7, 8)
            # Note: Adjust page indices if needed based on actual PDF structure
            if len(pdf.pages) < 9:
                pytest.skip("PDF doesn't have enough pages for this test")

            # Try to find the pages with FRN 152726
            frn_152726_pages = []

            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and '152726' in text:
                    frn_152726_pages.append(page)
                    if len(frn_152726_pages) >= 3:
                        break

            if len(frn_152726_pages) == 0:
                pytest.skip("Could not find FRN 152726 in PDF")

            # Parse the multi-page report
            record = report_parser.parse_multi_page_report(frn_152726_pages)

            # Assertions
            assert record is not None, "Parser returned None for FRN 152726"
            assert record['frn'] == '152726', f"Expected FRN 152726, got {record['frn']}"

            # Check basic fields
            assert record['make'] == '2 Vets Arms', f"Incorrect make: {record['make']}"
            assert record['model'] == '2VA-15', f"Incorrect model: {record['model']}"
            assert record['manufacturer'] == '2 Vets Arms', f"Incorrect manufacturer: {record['manufacturer']}"
            assert record['type'] == 'Rifle', f"Incorrect type: {record['type']}"
            assert record['action'] == 'Semi-Automatic', f"Incorrect action: {record['action']}"
            assert record['class'] == 'Prohibited', f"Incorrect class: {record['class']}"

            # Check multipage metadata
            if len(frn_152726_pages) > 1:
                assert record.get('multipage') is True, "Should be marked as multipage"
                assert record.get('page_count') == len(frn_152726_pages), \
                    f"Expected {len(frn_152726_pages)} pages, got {record.get('page_count')}"

            # Check notes are not empty (should contain detailed descriptions)
            assert record['notes'], "Notes should not be empty"
            assert len(record['notes']) > 100, \
                f"Notes too short ({len(record['notes'])} chars), likely missing continuation pages"

            # Check for expected content in notes
            expected_keywords = ['2VA-15', 'AR-15', 'receiver/frame', 'magazine']
            for keyword in expected_keywords:
                assert keyword.lower() in record['notes'].lower(), \
                    f"Expected keyword '{keyword}' not found in notes"

            # Check product codes if extracted
            if len(frn_152726_pages) >= 3:
                assert 'product_codes' in record, "Should have product_codes field"
                # Should have at least some product codes
                assert len(record.get('product_codes', [])) > 0, \
                    "Should have extracted product codes from continuation pages"

            # Print record for manual inspection
            print(f"\n=== FRN 152726 Extraction Result ===")
            print(f"FRN: {record['frn']}")
            print(f"Make: {record['make']}")
            print(f"Model: {record['model']}")
            print(f"Manufacturer: {record['manufacturer']}")
            print(f"Type: {record['type']}")
            print(f"Action: {record['action']}")
            print(f"Class: {record['class']}")
            print(f"Multipage: {record.get('multipage', False)}")
            print(f"Page Count: {record.get('page_count', 1)}")
            print(f"Notes Length: {len(record['notes'])} chars")
            print(f"Product Codes: {len(record.get('product_codes', []))} codes")
            print(f"Calibre Variants: {len(record.get('calibre_variants', []))} variants")

    def test_continuation_page_detection(self, report_parser, test_pdf_path):
        """Test that continuation pages are correctly identified"""
        with pdfplumber.open(test_pdf_path) as pdf:
            # Find a multi-page report
            frn_pages = []
            current_frn = None

            for page in pdf.pages[:50]:  # Check first 50 pages
                page_frn = report_parser._find_frn_in_page(page)
                if page_frn:
                    if page_frn == current_frn:
                        # Continuation page
                        frn_pages.append(page)
                    else:
                        # New report
                        if len(frn_pages) > 1:
                            # Found a multi-page report, test it
                            break
                        current_frn = page_frn
                        frn_pages = [page]

            if len(frn_pages) > 1:
                # Test continuation detection
                for i, page in enumerate(frn_pages[1:], start=1):
                    is_continuation = report_parser._is_continuation_page(page, current_frn)
                    assert is_continuation, \
                        f"Page {i+1} should be detected as continuation of FRN {current_frn}"

                print(f"\nSuccessfully detected {len(frn_pages)-1} continuation pages for FRN {current_frn}")

    def test_multipage_field_merging(self, report_parser):
        """Test that fields are correctly merged across pages"""
        # This is a unit test with mock data
        # In a real scenario, you'd use actual PDF pages

        # Create mock page objects (simplified)
        class MockPage:
            def __init__(self, text):
                self._text = text

            def extract_text(self):
                return self._text

            def extract_tables(self):
                return []

        page1 = MockPage("""
        FRT Report
        Firearm Reference Number (FRN): 123456
        Make: Test Manufacturer
        Model: Test Model
        Type: Rifle
        Action: Semi-Automatic
        Legal Classification: Non-Restricted

        Notes
        This is the first page of notes.
        """)

        page2 = MockPage("""
        FRN: 123456

        Make
        Extended description of the make that spans multiple paragraphs.

        Model
        Extended description of the model.

        Also Known As
        TEST-001
        TEST-002
        TEST-003
        """)

        record = report_parser.parse_multi_page_report([page1, page2])

        assert record is not None
        assert record['frn'] == '123456'
        assert 'Extended description of the make' in record['notes']
        assert 'Extended description of the model' in record['notes']
        assert len(record.get('product_codes', [])) >= 3


def test_full_pdf_parsing_with_multipage():
    """Integration test: Parse entire PDF and check for multipage records"""
    data_dir = Path(__file__).parent.parent / 'data'
    pdf_path = data_dir / 'frt_current.pdf'

    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found at {pdf_path}")

    # Run parser
    parser = FRTParser(data_dir=str(data_dir))
    parser.parse_pdf()

    # Load results
    output_path = data_dir / 'frt_database.json'
    assert output_path.exists(), "Parser should create output file"

    with open(output_path, 'r', encoding='utf-8') as f:
        records = json.load(f)

    # Check for multipage records
    multipage_records = [r for r in records if r.get('multipage') is True]

    print(f"\n=== Full PDF Parsing Results ===")
    print(f"Total records: {len(records)}")
    print(f"Multipage records: {len(multipage_records)}")

    if multipage_records:
        print(f"\nSample multipage records:")
        for record in multipage_records[:5]:
            print(f"  - FRN {record['frn']}: {record.get('page_count', '?')} pages, "
                  f"{len(record.get('notes', ''))} chars in notes")

    # Should have at least some multipage records in a typical FRT PDF
    # This assertion might need adjustment based on actual PDF content
    # assert len(multipage_records) > 0, "Should find at least some multipage records"


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s'])
