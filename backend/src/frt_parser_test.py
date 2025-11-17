#!/usr/bin/env python3
"""
FRT-Live PDF Parser - Test Version (2000 Pages Max)
Limited version for testing parsing logic on first 2000 pages
"""

import pdfplumber
import json
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter
from tqdm import tqdm

# Import the original parser
from frt_parser import FRTParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/frt_parser_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FRTParserTest(FRTParser):
    """
    Test version of FRT Parser that only processes the first 2000 pages.
    Useful for validating parsing logic before running on complete dataset.
    """

    def __init__(self, data_dir: str = 'data', output_file: str = 'frt_database_test.json',
                 pdf_url: str = None, max_pages: int = 2000):
        """
        Initialize the FRT Parser Test version

        Args:
            data_dir: Directory to store downloaded PDFs
            output_file: Output JSON file path (defaults to test file)
            pdf_url: Optional direct PDF URL (overrides default)
            max_pages: Maximum number of pages to process (default: 2000)
        """
        super().__init__(data_dir=data_dir, output_file=output_file, pdf_url=pdf_url)
        self.max_pages = max_pages
        logger.info(f"Test parser initialized with max_pages={max_pages}")

    def parse_pdf(self) -> int:
        """
        Parse the PDF and extract firearm records (limited to first max_pages pages)

        Returns:
            Number of records extracted
        """
        if not self.pdf_path.exists():
            logger.error("PDF file not found. Please download first.")
            return 0

        try:
            logger.info(f"Opening PDF: {self.pdf_path}")

            records = []
            current_record = None

            with pdfplumber.open(self.pdf_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_process = min(self.max_pages, total_pages)

                logger.info(f"PDF has {total_pages} pages")
                logger.info(f"TEST MODE: Processing only first {pages_to_process} pages")

                # Detect column boundaries
                if not self.detect_column_boundaries(pdf):
                    logger.error("Failed to detect column boundaries")
                    logger.info("Attempting to parse using table extraction without column boundaries...")

                    # Fallback method with page limit
                    for page_num in range(pages_to_process):
                        page = pdf.pages[page_num]
                        tables = page.extract_tables()

                        if not tables:
                            continue

                        for table in tables:
                            # First row might be headers
                            if not table or len(table) < 2:
                                continue

                            # Try to identify columns from first row
                            header_row = table[0]
                            if header_row:
                                # Map columns dynamically
                                col_mapping = {}
                                for idx, cell in enumerate(header_row):
                                    if cell:
                                        cell_upper = str(cell).upper().strip()
                                        for expected in self.EXPECTED_COLUMNS:
                                            if expected.upper() in cell_upper or cell_upper in expected.upper():
                                                col_mapping[idx] = expected
                                                break

                                # Process data rows
                                for row in table[1:]:
                                    if not row or all(not cell for cell in row):
                                        continue

                                    # Extract FRN to check if it's a new record
                                    frn_idx = next((idx for idx, col in col_mapping.items() if col == 'FRN'), None)
                                    if frn_idx is None or frn_idx >= len(row):
                                        continue

                                    frn = str(row[frn_idx]).strip() if row[frn_idx] else ""

                                    if self.is_valid_frn(frn):
                                        if current_record:
                                            records.append(current_record)

                                        current_record = {
                                            'frn': frn,
                                            'make': '',
                                            'model': '',
                                            'manufacturer': '',
                                            'type': '',
                                            'action': '',
                                            'class': 'Unknown',
                                            'notes': '',
                                            'oic_references': []
                                        }

                                        # Fill in other fields from column mapping
                                        for idx, col_name in col_mapping.items():
                                            if idx < len(row) and row[idx]:
                                                field_name = col_name.lower()
                                                value = str(row[idx]).strip()
                                                if col_name == 'Class':
                                                    current_record[field_name] = self.sanitize_class(value)
                                                else:
                                                    current_record[field_name] = value

                        # Progress update every 100 pages
                        if (page_num + 1) % 100 == 0:
                            logger.info(f"TEST: Processed {page_num + 1}/{pages_to_process} pages, {len(records)} records so far")

                    if current_record:
                        records.append(current_record)

                    if not records:
                        logger.error("No records extracted using fallback method")
                        return 0

                    logger.info(f"TEST: Extracted {len(records)} records using fallback table extraction")

                else:
                    # Normal processing with detected column boundaries (LIMITED TO max_pages)
                    logger.info("Using column-based text extraction")

                    # First pass: Classify pages (sample first 100 pages for efficiency)
                    logger.info("Classifying page types...")
                    page_types = {}
                    sample_size = min(100, pages_to_process)
                    for i in range(sample_size):
                        page_type = self.page_classifier.classify(pdf.pages[i])
                        page_types[i + 1] = page_type

                    # Log page type statistics
                    type_counts = Counter(page_types.values())
                    logger.info(f"Page classification (first {sample_size} pages): {dict(type_counts)}")

                    # For remaining pages up to max_pages, assume TABLE unless proven otherwise
                    for i in range(sample_size, pages_to_process):
                        page_types[i + 1] = 'TABLE'  # Default assumption

                    # Track statistics
                    skipped_pages = 0
                    processed_pages = 0

                    # Process each page (LIMITED TO max_pages)
                    pages_to_iterate = pdf.pages[:pages_to_process]

                    for page_num, page in enumerate(tqdm(pages_to_iterate, desc=f"Processing pages (max {pages_to_process})")):
                        # Check page type
                        page_type = page_types.get(page_num + 1, 'TABLE')

                        # Skip non-table pages (REPORT, COVER pages don't contain tabular data)
                        if page_type in ['REPORT', 'COVER']:
                            skipped_pages += 1
                            logger.debug(f"Skipping page {page_num + 1} (type: {page_type})")
                            continue

                        processed_pages += 1

                        # Extract words to identify text rows
                        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)

                        if not words:
                            continue

                        # Group words by y-position to identify rows
                        rows_dict = {}
                        for word in words:
                            y_pos = round(word['top'], 0)  # Round to nearest pixel
                            if y_pos not in rows_dict:
                                rows_dict[y_pos] = []
                            rows_dict[y_pos].append(word)

                        # Sort rows by y position
                        sorted_y_positions = sorted(rows_dict.keys())

                        # Process each row
                        for y_pos in sorted_y_positions:
                            row_words = rows_dict[y_pos]

                            # Skip if this looks like a header row
                            if page_num < 5:  # Only check first few pages
                                row_text = ' '.join([w['text'] for w in row_words]).upper()
                                if any(header in row_text for header in ['FRN', 'MAKE', 'MODEL', 'CLASS', 'MANUFACTURER']):
                                    continue

                            # Extract text from each column for this row
                            row_dict = {}
                            for col_name, (x_start, x_end) in self.column_boundaries.items():
                                # Get words in this column - check if word's center is within column bounds
                                col_words = []
                                for w in row_words:
                                    word_center = (w['x0'] + w['x1']) / 2
                                    # Word belongs to this column if its center is within the boundaries
                                    if x_start <= word_center < x_end:
                                        col_words.append(w)
                                col_text = ' '.join([w['text'] for w in col_words])
                                row_dict[col_name] = col_text.strip()

                            # Check if this is a new record (has valid FRN) or continuation
                            frn = row_dict.get('FRN', '').strip()

                            # Use enhanced validation to check if this is a data row
                            if self.is_valid_frn(frn) and self.is_data_row(row_dict):
                                # Save previous record if exists
                                if current_record:
                                    records.append(current_record)

                                # Start new record
                                current_record = {
                                    'frn': frn,
                                    'make': row_dict.get('Make', '').strip(),
                                    'model': row_dict.get('Model', '').strip(),
                                    'manufacturer': row_dict.get('Manufacturer', '').strip(),
                                    'type': row_dict.get('Type', '').strip(),
                                    'action': row_dict.get('Action', '').strip(),
                                    'class': self.sanitize_class(row_dict.get('Class', '')),
                                    'notes': row_dict.get('Notes', '').strip(),
                                    'oic_references': []
                                }
                            else:
                                # This is a continuation row - append to current record
                                if current_record:
                                    # Append text to existing fields (usually Notes)
                                    for col_name in self.EXPECTED_COLUMNS:
                                        if col_name != 'FRN' and row_dict.get(col_name, '').strip():
                                            field_name = col_name.lower()
                                            if field_name in current_record:
                                                current_record[field_name] += ' ' + row_dict[col_name].strip()

                        # Progress logging every 100 pages
                        if (page_num + 1) % 100 == 0:
                            logger.info(f"TEST: Processed {page_num + 1}/{pages_to_process} pages, {len(records)} records so far")

                    # Add the last record
                    if current_record:
                        records.append(current_record)

                    # Log page processing statistics
                    logger.info(f"TEST: Page processing complete: {processed_pages} table pages processed, {skipped_pages} pages skipped")

            # Post-process: Extract OIC references
            logger.info("Extracting OIC references from notes")
            for record in records:
                record['oic_references'] = self.extract_oic_references(record.get('notes', ''))

            # Write to JSON file
            logger.info(f"Writing {len(records)} records to {self.output_file}")

            with open(self.output_file, 'w', encoding='utf-8') as f:
                # Write array opening
                f.write('[\n')

                for idx, record in enumerate(records):
                    # Write record
                    json.dump(record, f, ensure_ascii=False, indent=2)

                    # Add comma if not last record
                    if idx < len(records) - 1:
                        f.write(',\n')
                    else:
                        f.write('\n')

                # Write array closing
                f.write(']\n')

            logger.info(f"TEST: Successfully parsed {len(records)} firearm records from first {pages_to_process} pages")

            # Save summary metadata
            summary = {
                'total_records': len(records),
                'pages_processed': pages_to_process,
                'total_pages_in_pdf': total_pages,
                'test_mode': True,
                'max_pages_limit': self.max_pages,
                'parse_date': datetime.now().isoformat(),
                'pdf_file': str(self.pdf_path),
                'output_file': str(self.output_file)
            }

            summary_path = self.data_dir / 'parse_summary_test.json'
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)

            logger.info(f"TEST: Summary saved to {summary_path}")

            return len(records)

        except Exception as e:
            logger.error(f"Error parsing PDF: {e}", exc_info=True)
            return 0


def main():
    """Main entry point for test parser"""
    import argparse

    arg_parser = argparse.ArgumentParser(
        description='Parse RCMP Firearms Reference Table PDF (TEST VERSION - 2000 pages max)',
        epilog="""
Examples:
  # Parse first 2000 pages using existing local PDF (skip download)
  python frt_parser_test.py --skip-download

  # Parse first 500 pages only
  python frt_parser_test.py --skip-download --max-pages 500

  # Force download and parse first 2000 pages
  python frt_parser_test.py --force

  # Use custom PDF URL
  python frt_parser_test.py --url "https://example.com/frt.pdf" --skip-download
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    arg_parser.add_argument('--force', action='store_true', help='Force download even if cached')
    arg_parser.add_argument('--skip-download', action='store_true', help='Skip download, use existing PDF file')
    arg_parser.add_argument('--data-dir', default='data', help='Data directory path')
    arg_parser.add_argument('--output', default='frt_database_test.json', help='Output JSON filename')
    arg_parser.add_argument('--url', help='Direct PDF URL (overrides default)')
    arg_parser.add_argument('--max-pages', type=int, default=2000, help='Maximum pages to process (default: 2000)')

    args = arg_parser.parse_args()

    # Create logs directory
    Path('logs').mkdir(exist_ok=True)

    # Run test parser
    frt_parser = FRTParserTest(
        data_dir=args.data_dir,
        output_file=args.output,
        pdf_url=args.url,
        max_pages=args.max_pages
    )
    frt_parser.run(force_download=args.force, skip_download=args.skip_download)


if __name__ == '__main__':
    main()
