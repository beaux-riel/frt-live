#!/usr/bin/env python3
"""
FRT-Live PDF Parser
Automated ingestion and parsing of the RCMP Firearms Reference Table
"""

import pdfplumber
import requests
import json
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dateutil import parser as date_parser
from tqdm import tqdm


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/frt_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FRTParser:
    """Parser for RCMP Firearms Reference Table PDFs"""

    # RCMP FRT URL (update this with direct PDF link if known)
    FRT_URL = "https://rcmp.ca/sites/default/files/dam/frt-1103.pdf"

    # Browser headers to avoid 403 errors
    BROWSER_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # Expected column headers in the FRT PDF
    EXPECTED_COLUMNS = ['FRN', 'Make', 'Model', 'Manufacturer', 'Type', 'Action', 'Class', 'Notes']

    # Standard classifications
    STANDARD_CLASSES = {
        'NR': 'Non-Restricted',
        'NON-RESTRICTED': 'Non-Restricted',
        'NON RESTRICTED': 'Non-Restricted',
        'R': 'Restricted',
        'RESTRICTED': 'Restricted',
        'P': 'Prohibited',
        'PROHIBITED': 'Prohibited',
        '12(2)': 'Prohibited',
        '12(3)': 'Prohibited',
        '12(4)': 'Prohibited',
        '12(5)': 'Prohibited',
        '12(6)': 'Prohibited',
        '12(7)': 'Prohibited',
    }

    def __init__(self, data_dir: str = 'data', output_file: str = 'frt_database.json', pdf_url: Optional[str] = None):
        """
        Initialize the FRT Parser

        Args:
            data_dir: Directory to store downloaded PDFs
            output_file: Output JSON file path
            pdf_url: Optional direct PDF URL (overrides default)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.output_file = self.data_dir / output_file
        self.pdf_path = self.data_dir / 'frt_current.pdf'
        self.metadata_path = self.data_dir / 'frt_metadata.json'

        # Use custom URL if provided
        if pdf_url:
            self.FRT_URL = pdf_url

        # Column boundaries (will be detected from PDF)
        self.column_boundaries: Dict[str, Tuple[float, float]] = {}

    def check_for_updates(self) -> bool:
        """
        Check if the remote PDF has been updated

        Returns:
            True if update is available or no local file exists
        """
        try:
            logger.info(f"Checking for updates at {self.FRT_URL}")

            # Make HEAD request to check Last-Modified header with browser headers
            response = requests.head(
                self.FRT_URL,
                headers=self.BROWSER_HEADERS,
                allow_redirects=True,
                timeout=10
            )
            response.raise_for_status()

            # Log if we were redirected
            if response.url != self.FRT_URL:
                logger.info(f"Redirected to: {response.url}")

            remote_last_modified = response.headers.get('Last-Modified')
            if not remote_last_modified:
                logger.warning("No Last-Modified header found, proceeding with download")
                return True

            remote_date = date_parser.parse(remote_last_modified)

            # Check if we have local metadata
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r') as f:
                    metadata = json.load(f)
                    local_date = date_parser.parse(metadata.get('last_modified', '1970-01-01'))

                    if remote_date <= local_date:
                        logger.info(f"Local file is up-to-date (remote: {remote_date}, local: {local_date})")
                        return False
                    else:
                        logger.info(f"Update available (remote: {remote_date}, local: {local_date})")
                        return True

            logger.info("No local metadata found, proceeding with download")
            return True

        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            # If check fails but we have a local file, use it
            return not self.pdf_path.exists()

    def download_pdf(self, force: bool = False) -> bool:
        """
        Download the FRT PDF if needed

        Args:
            force: Force download even if up-to-date

        Returns:
            True if download was successful or file exists
        """
        try:
            # Check if update is needed
            if not force and not self.check_for_updates():
                logger.info("Using cached PDF file")
                return True

            logger.info(f"Downloading FRT PDF from {self.FRT_URL}")

            # Use browser headers to avoid 403 errors
            response = requests.get(
                self.FRT_URL,
                headers=self.BROWSER_HEADERS,
                stream=True,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()

            # Check if we got HTML instead of PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                logger.error(
                    f"Received HTML page instead of PDF. "
                    f"The URL '{self.FRT_URL}' may be a web page, not a direct PDF link."
                )
                logger.error(
                    "Please find the actual PDF download link and either:\n"
                    "  1. Set FRT_PDF_URL environment variable, or\n"
                    "  2. Pass pdf_url parameter to FRTParser, or\n"
                    "  3. Manually download PDF to data/frt_current.pdf"
                )
                return False

            # Log if we were redirected
            if response.url != self.FRT_URL:
                logger.info(f"Redirected to: {response.url}")

            # Get total file size for progress bar
            total_size = int(response.headers.get('content-length', 0))

            # Download with progress bar
            with open(self.pdf_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading') as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            # Verify it's actually a PDF
            with open(self.pdf_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    logger.error("Downloaded file is not a valid PDF!")
                    logger.error("Please check the URL or manually download the PDF to data/frt_current.pdf")
                    return False

            # Save metadata
            metadata = {
                'last_modified': response.headers.get('Last-Modified', datetime.now().isoformat()),
                'download_date': datetime.now().isoformat(),
                'file_size': os.path.getsize(self.pdf_path),
                'url': self.FRT_URL,
                'actual_url': response.url
            }

            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"PDF downloaded successfully ({total_size / 1024 / 1024:.2f} MB)")
            return True

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error downloading PDF: {e}")
            logger.error(
                "\nTroubleshooting:\n"
                "  - The URL may have changed. Check the RCMP website for the latest FRT PDF.\n"
                "  - The website may be blocking automated requests.\n"
                "  - You can manually download the PDF and place it in: data/frt_current.pdf\n"
                f"  - Current URL: {self.FRT_URL}"
            )
            return False
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return False

    def detect_column_boundaries(self, pdf: pdfplumber.PDF) -> bool:
        """
        Detect column boundaries from the PDF header
        Tries multiple pages if the first page doesn't contain headers

        Args:
            pdf: pdfplumber PDF object

        Returns:
            True if columns were detected successfully
        """
        try:
            logger.info("Detecting column boundaries from PDF header")

            # Try first few pages to find headers (some PDFs have cover pages)
            max_pages_to_check = min(10, len(pdf.pages))

            for page_idx in range(max_pages_to_check):
                page = pdf.pages[page_idx]

                # Extract words with their positions
                words = page.extract_words(x_tolerance=3, y_tolerance=3)

                if not words:
                    logger.warning(f"Page {page_idx + 1}: No text found, trying next page")
                    continue

                # Find header row by looking for expected column names
                # Use fuzzy matching - look for partial matches
                header_words = []
                for word in words:
                    word_upper = word['text'].upper().strip()
                    # Check for exact and partial matches
                    for expected_col in self.EXPECTED_COLUMNS:
                        expected_upper = expected_col.upper()
                        # Match if the word contains the column name or vice versa
                        # Also handle common variations like "MAKE/MODEL" split across words
                        if (expected_upper in word_upper or
                            word_upper in expected_upper or
                            word_upper == expected_upper.replace(' ', '') or
                            expected_upper.replace(' ', '') in word_upper):
                            # Avoid duplicates
                            if not any(hw['text'].upper() == word_upper for hw in header_words):
                                header_words.append(word)
                                break

                logger.info(f"Page {page_idx + 1}: Found {len(header_words)} potential column headers")

                # If we found enough headers, use this page
                if len(header_words) >= 4:  # At least need FRN, Make, Model, Class
                    logger.info(f"Using page {page_idx + 1} for column detection")

                    # Sort by x position
                    header_words.sort(key=lambda w: w['x0'])

                    # Create column boundaries
                    page_width = page.width

                    for i, word in enumerate(header_words):
                        col_name = None
                        word_upper = word['text'].upper().strip()

                        # Match to expected columns
                        for expected in self.EXPECTED_COLUMNS:
                            expected_upper = expected.upper()
                            if (expected_upper in word_upper or
                                word_upper in expected_upper or
                                word_upper == expected_upper.replace(' ', '')):
                                col_name = expected
                                break

                        if col_name:
                            x_start = word['x0']
                            # x_end is the start of the next column or page width
                            x_end = header_words[i + 1]['x0'] if i + 1 < len(header_words) else page_width
                            self.column_boundaries[col_name] = (x_start, x_end)

                    logger.info(f"Detected {len(self.column_boundaries)} columns: {list(self.column_boundaries.keys())}")

                    # Ensure we have at least FRN, Make, Model, and Class
                    required = ['FRN', 'Make', 'Model', 'Class']
                    missing = [col for col in required if col not in self.column_boundaries]

                    if not missing:
                        return True
                    else:
                        logger.warning(f"Page {page_idx + 1}: Missing required columns: {missing}, trying next page")
                        # Clear boundaries and try next page
                        self.column_boundaries = {}

            # If we get here, we didn't find headers on any page
            logger.error(f"Failed to find column headers in first {max_pages_to_check} pages")
            logger.error("Missing required columns: ['FRN', 'Make', 'Model', 'Class']")
            return False

        except Exception as e:
            logger.error(f"Error detecting column boundaries: {e}", exc_info=True)
            return False

    def extract_text_in_bbox(self, page, bbox: Tuple[float, float, float, float]) -> str:
        """
        Extract text within a bounding box

        Args:
            page: pdfplumber page object
            bbox: Bounding box (x0, y0, x1, y1)

        Returns:
            Extracted text
        """
        try:
            cropped = page.crop(bbox)
            text = cropped.extract_text()
            return text.strip() if text else ""
        except:
            return ""

    def extract_row(self, page, y_start: float, y_end: float) -> Dict[str, str]:
        """
        Extract a single row based on y-coordinates

        Args:
            page: pdfplumber page object
            y_start: Top y-coordinate
            y_end: Bottom y-coordinate

        Returns:
            Dictionary with column values
        """
        row = {}

        for col_name, (x_start, x_end) in self.column_boundaries.items():
            bbox = (x_start, y_start, x_end, y_end)
            text = self.extract_text_in_bbox(page, bbox)
            row[col_name] = text

        return row

    def is_valid_frn(self, frn: str) -> bool:
        """
        Check if a string is a valid FRN (Firearm Reference Number)

        Args:
            frn: String to check

        Returns:
            True if valid FRN format
        """
        if not frn:
            return False
        # FRN is typically numeric, possibly with hyphens or letters
        # Example formats: 123456, 12345-A, etc.
        return bool(re.match(r'^[\d\-A-Za-z]+$', frn.strip()))

    def sanitize_class(self, class_value: str) -> str:
        """
        Standardize classification values

        Args:
            class_value: Raw classification string

        Returns:
            Standardized classification
        """
        if not class_value:
            return "Unknown"

        # Clean up the value
        clean = class_value.strip().upper()

        # Check against known values
        for key, standard in self.STANDARD_CLASSES.items():
            if key in clean:
                return standard

        # Return original if no match
        logger.warning(f"Unknown classification value: {class_value}")
        return class_value.strip()

    def extract_oic_references(self, notes: str) -> List[str]:
        """
        Extract OIC (Order in Council) references from notes

        Args:
            notes: Notes text

        Returns:
            List of OIC references
        """
        if not notes:
            return []

        # Pattern to match OIC references (e.g., "OIC 2020-123", "OIC #2020-0001")
        pattern = r'OIC\s*#?\s*(\d{4}-\d{3,4})'
        matches = re.findall(pattern, notes, re.IGNORECASE)

        return [f"OIC {match}" for match in matches]

    def parse_pdf(self) -> int:
        """
        Parse the PDF and extract all firearm records

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
                logger.info(f"PDF has {len(pdf.pages)} pages")

                # Detect column boundaries
                if not self.detect_column_boundaries(pdf):
                    logger.error("Failed to detect column boundaries")
                    logger.info("Attempting to parse using table extraction without column boundaries...")

                    # Try parsing without column boundaries using table auto-detection
                    # This is a fallback method
                    for page_num, page in enumerate(tqdm(pdf.pages, desc="Processing pages (fallback mode)")):
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

                    if current_record:
                        records.append(current_record)

                    if not records:
                        logger.error("No records extracted using fallback method")
                        return 0

                    logger.info(f"Extracted {len(records)} records using fallback table extraction")

                else:
                    # Normal processing with detected column boundaries
                    # Process each page
                    for page_num, page in enumerate(tqdm(pdf.pages, desc="Processing pages")):
                        # Extract tables (pdfplumber can detect table structure)
                        tables = page.extract_tables()

                        if not tables:
                            if page_num < 20:  # Only warn for first few pages
                                logger.warning(f"No tables found on page {page_num + 1}")
                            continue

                        # Process the first (main) table on the page
                        table = tables[0]

                        for row_idx, row in enumerate(table):
                            # Skip header rows on first page
                            if row_idx == 0 and page_num < 2:
                                # Check if this looks like a header row
                                if row and any(str(cell).upper() in ['FRN', 'MAKE', 'MODEL', 'CLASS'] for cell in row if cell):
                                    continue

                            # Handle empty rows
                            if not row or all(not cell for cell in row):
                                continue

                            # Map row to columns (assuming column order matches EXPECTED_COLUMNS)
                            row_dict = {}
                            for col_idx, col_name in enumerate(self.EXPECTED_COLUMNS):
                                if col_idx < len(row):
                                    row_dict[col_name] = str(row[col_idx]).strip() if row[col_idx] else ""
                                else:
                                    row_dict[col_name] = ""

                            # Check if this is a new record (has valid FRN) or continuation
                            frn = row_dict.get('FRN', '').strip()

                            if self.is_valid_frn(frn):
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

                    # Add the last record
                    if current_record:
                        records.append(current_record)

            # Post-process: Extract OIC references
            logger.info("Extracting OIC references from notes")
            for record in records:
                record['oic_references'] = self.extract_oic_references(record.get('notes', ''))

            # Write to JSON file (streaming approach for large datasets)
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

            logger.info(f"Successfully parsed {len(records)} firearm records")

            # Save summary metadata
            summary = {
                'total_records': len(records),
                'parse_date': datetime.now().isoformat(),
                'pdf_file': str(self.pdf_path),
                'output_file': str(self.output_file)
            }

            summary_path = self.data_dir / 'parse_summary.json'
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)

            return len(records)

        except Exception as e:
            logger.error(f"Error parsing PDF: {e}", exc_info=True)
            return 0

    def run(self, force_download: bool = False, skip_download: bool = False):
        """
        Run the complete FRT parsing pipeline

        Args:
            force_download: Force download even if cached version exists
            skip_download: Skip download and use existing PDF file
        """
        logger.info("=" * 50)
        logger.info("FRT-Live PDF Parser Starting")
        logger.info("=" * 50)

        # Step 1: Download PDF (unless skipped)
        if not skip_download:
            if not self.download_pdf(force=force_download):
                logger.warning("Failed to download PDF")

                # Check if we have a local PDF to work with
                if self.pdf_path.exists():
                    logger.info(f"Found existing PDF file: {self.pdf_path}")
                    logger.info("Proceeding with local file...")
                else:
                    logger.error("No local PDF file available")
                    logger.error(f"Please manually download the FRT PDF and place it at: {self.pdf_path}")
                    return
        else:
            logger.info("Skipping download, using existing PDF file")
            if not self.pdf_path.exists():
                logger.error(f"PDF file not found: {self.pdf_path}")
                logger.error("Please download the FRT PDF first or run without --skip-download")
                return

        # Step 2: Parse PDF
        record_count = self.parse_pdf()

        if record_count > 0:
            logger.info("=" * 50)
            logger.info(f"SUCCESS: Parsed {record_count} records")
            logger.info(f"Output: {self.output_file}")
            logger.info("=" * 50)
        else:
            logger.error("Failed to parse PDF")


def main():
    """Main entry point"""
    import argparse

    arg_parser = argparse.ArgumentParser(
        description='Parse RCMP Firearms Reference Table PDF',
        epilog="""
Examples:
  # Parse using existing local PDF (skip download)
  python frt_parser.py --skip-download

  # Force download and parse
  python frt_parser.py --force

  # Use custom PDF URL
  python frt_parser.py --url "https://example.com/frt.pdf"

  # Manually place PDF and parse
  # 1. Download PDF to backend/data/frt_current.pdf
  # 2. Run: python frt_parser.py --skip-download
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    arg_parser.add_argument('--force', action='store_true', help='Force download even if cached')
    arg_parser.add_argument('--skip-download', action='store_true', help='Skip download, use existing PDF file')
    arg_parser.add_argument('--data-dir', default='data', help='Data directory path')
    arg_parser.add_argument('--output', default='frt_database.json', help='Output JSON filename')
    arg_parser.add_argument('--url', help='Direct PDF URL (overrides default)')

    args = arg_parser.parse_args()

    # Create logs directory
    Path('logs').mkdir(exist_ok=True)

    # Run parser
    frt_parser = FRTParser(data_dir=args.data_dir, output_file=args.output, pdf_url=args.url)
    frt_parser.run(force_download=args.force, skip_download=args.skip_download)


if __name__ == '__main__':
    main()
