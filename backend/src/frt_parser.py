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
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dateutil import parser as date_parser
from tqdm import tqdm

# Import page classifier and report parser
from page_classifier import PageClassifier
from frt_report_parser import FRTReportParser


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

        # Page classifier for detecting page types
        self.page_classifier = PageClassifier()

        # Report parser for extracting data from individual report pages
        self.report_parser = FRTReportParser()

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

        frn = frn.strip()

        # FRN should be primarily numeric
        # Valid formats: 123456, 12345-1, 12345-A, etc.
        # Must have at least 3 digits
        digit_count = sum(1 for c in frn if c.isdigit())
        if digit_count < 3:
            return False

        # Check pattern: alphanumeric with optional hyphens
        if not re.match(r'^[\d\-A-Za-z]+$', frn):
            return False

        # Should not be too long (FRNs are typically 5-7 characters)
        if len(frn) > 15:
            return False

        # Should not start with common non-FRN words
        non_frn_prefixes = ['page', 'frt', 'note', 'see', 'model', 'make']
        if any(frn.lower().startswith(prefix) for prefix in non_frn_prefixes):
            return False

        return True

    def is_data_row(self, row_dict: Dict[str, str]) -> bool:
        """
        Validate if a row contains actual firearm data (not headers/notes/sections)

        Args:
            row_dict: Dictionary with column values

        Returns:
            True if this appears to be a data row
        """
        # Must have valid FRN
        frn = row_dict.get('FRN', '').strip()
        if not self.is_valid_frn(frn):
            return False

        # Should have at least 2 of the core fields populated
        core_fields = ['Make', 'Model', 'Class']
        populated_count = sum(
            1 for field in core_fields
            if row_dict.get(field, '').strip() and len(row_dict.get(field, '').strip()) > 1
        )

        if populated_count < 2:
            return False

        # Class field should not be a common word from notes
        class_value = row_dict.get('Class', '').strip()
        if class_value:
            # Check if it looks like a classification
            class_upper = class_value.upper()
            is_valid_class = any(
                key in class_upper for key in self.STANDARD_CLASSES.keys()
            )

            # If class doesn't match any standard format and is a common word, reject
            if not is_valid_class and len(class_value.split()) == 1:
                # Single words that are clearly not classifications
                common_words = {
                    'THE', 'AND', 'OR', 'WITH', 'FOR', 'FROM', 'THAT', 'THIS',
                    'HAVE', 'BEEN', 'WERE', 'THEIR', 'ABOVE', 'BELOW', 'BETWEEN'
                }
                if class_upper in common_words:
                    return False

        return True

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

        # Only warn if this genuinely looks like a classification attempt
        # Don't warn on obvious misclassified notes text
        should_warn = (
            len(clean) <= 20 and
            len(clean.split()) <= 2 and  # Max 2 words
            any(indicator in clean for indicator in ['R', 'P', 'N', '12(', 'RESTRICT', 'PROHIBIT']) and
            # Exclude common words that got misclassified
            clean not in {'AND', 'OR', 'THE', 'WITH', 'FOR', 'FROM', 'ABOVE', 'BELOW',
                         'MOUNTED', 'SYNTHETIC', 'ACTION', 'SOUND', 'MAGAZINE', 'VENTILATED',
                         'DIMENSIONS', 'SHOTGUNS', 'NICKELED', 'BLADE', 'STOCK', 'BULLET',
                         'CHEEK', 'WINDAGE', 'WOODEN', 'CUSTOM', 'THAT', 'THIS', 'BEEN'}
        )

        if should_warn:
            logger.warning(f"Unknown classification value: {class_value}")

        # Return original if no match, or "Unknown" if it's clearly not a classification
        if len(clean) > 20 or len(clean.split()) > 3:
            return "Unknown"

        # If it's a single common word, return Unknown
        if clean in {'AND', 'OR', 'THE', 'WITH', 'FOR', 'FROM', 'ABOVE', 'BELOW',
                     'MOUNTED', 'SYNTHETIC', 'ACTION', 'SOUND', 'MAGAZINE', 'VENTILATED',
                     'DIMENSIONS', 'SHOTGUNS', 'NICKELED', 'BLADE', 'STOCK', 'BULLET',
                     'CHEEK', 'WINDAGE', 'WOODEN', 'CUSTOM', 'THAT', 'THIS', 'BEEN'}:
            return "Unknown"

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
                # Get page count safely
                # pdfplumber.pdf.metadata contains page count without loading all pages
                try:
                    # Access metadata to get page count
                    page_count = len(pdf.pages)

                    # Validate page count (FRT PDFs are typically 200-500 pages)
                    if page_count > 10000:
                        logger.error(f"PDF reports {page_count} pages - this seems incorrect!")
                        logger.error("This likely indicates a corrupted or malformed PDF file.")
                        logger.error("Expected page count: 200-500 pages for FRT")
                        logger.error("Please verify the PDF file integrity or try re-downloading it.")
                        return 0

                    logger.info(f"PDF has {page_count} pages")
                except Exception as e:
                    logger.error(f"Error reading PDF page count: {e}")
                    return 0

                # Detect column boundaries
                if not self.detect_column_boundaries(pdf):
                    logger.error("Failed to detect column boundaries")
                    logger.info("Attempting to parse using table extraction without column boundaries...")

                    # Try parsing without column boundaries using table auto-detection
                    # This is a fallback method
                    for page_num in tqdm(range(page_count), desc="Processing pages (fallback mode)"):
                        page = pdf.pages[page_num]
                        tables = page.extract_tables()

                        if not tables:
                            logger.warning(f"No tables found on page {page_num + 1}")
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

                        # Periodic garbage collection in fallback mode
                        if (page_num + 1) % 100 == 0:
                            logger.info(f"Processed {page_num + 1} pages (fallback mode), {len(records)} records so far")
                            page.flush_cache()
                            gc.collect()

                    if current_record:
                        records.append(current_record)

                    if not records:
                        logger.error("No records extracted using fallback method")
                        return 0

                    logger.info(f"Extracted {len(records)} records using fallback table extraction")

                else:
                    # Normal processing with detected column boundaries
                    # Use text extraction with column boundaries instead of table extraction
                    logger.info("Using column-based text extraction")

                    # First pass: Classify pages (sample first 100 pages for efficiency)
                    logger.info("Classifying page types...")
                    page_types = {}
                    sample_size = min(100, page_count)
                    for i in range(sample_size):
                        page_type = self.page_classifier.classify(pdf.pages[i])
                        page_types[i + 1] = page_type

                    # Log page type statistics
                    from collections import Counter
                    type_counts = Counter(page_types.values())
                    logger.info(f"Page classification (first {sample_size} pages): {dict(type_counts)}")

                    # For remaining pages, assume TABLE unless proven otherwise
                    for i in range(sample_size, page_count):
                        page_types[i + 1] = 'TABLE'  # Default assumption

                    # Track statistics
                    skipped_pages = 0
                    table_pages = 0
                    report_pages = 0
                    cover_pages = 0

                    # Track multi-page reports
                    current_report_frn = None
                    report_pages_buffer = []

                    # Process each page using index-based access to avoid loading all pages
                    for page_num in tqdm(range(page_count), desc="Processing pages"):
                        page = pdf.pages[page_num]
                        # Check page type
                        page_type = page_types.get(page_num + 1, 'TABLE')

                        # Handle REPORT pages
                        if page_type == 'REPORT':
                            report_pages += 1

                            # Try to find FRN on this page
                            page_frn = self.report_parser._find_frn_in_page(page)

                            if page_frn:
                                # Check if this is a continuation of current report
                                if current_report_frn == page_frn:
                                    # Continuation page - add to buffer
                                    report_pages_buffer.append(page)
                                    logger.debug(f"Added continuation page {page_num + 1} for FRN {page_frn}")
                                else:
                                    # New report FRN detected
                                    # First, save previous buffered report if exists
                                    if report_pages_buffer and current_report_frn:
                                        logger.info(f"Processing {len(report_pages_buffer)}-page report for FRN {current_report_frn}")
                                        multi_report = self.report_parser.parse_multi_page_report(report_pages_buffer)
                                        if multi_report:
                                            records.append(multi_report)
                                        else:
                                            logger.warning(f"Failed to parse multi-page report for FRN {current_report_frn}")

                                    # Start new report buffer
                                    current_report_frn = page_frn
                                    report_pages_buffer = [page]
                                    logger.debug(f"Started new report buffer for FRN {page_frn} at page {page_num + 1}")
                            else:
                                # No FRN found - might be a continuation page
                                # Check if we have an active buffer
                                if current_report_frn and report_pages_buffer:
                                    # Assume it's a continuation
                                    report_pages_buffer.append(page)
                                    logger.debug(f"Added possible continuation page {page_num + 1} (no FRN) to FRN {current_report_frn}")
                                else:
                                    logger.warning(f"REPORT page {page_num + 1} has no FRN and no active buffer")

                            continue

                        # Skip cover pages
                        if page_type == 'COVER':
                            cover_pages += 1
                            logger.debug(f"Skipping page {page_num + 1} (type: COVER)")
                            continue

                        # Handle TABLE pages
                        table_pages += 1

                        # Extract words to identify text rows
                        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)

                        if not words:
                            continue

                        # Group words by y-position to identify rows
                        # Group words that are within 3 points vertically
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

                        # Periodic progress logging and memory management
                        if (page_num + 1) % 1000 == 0:
                            logger.info(f"Processed {page_num + 1} pages, {len(records)} records so far")
                            # Explicitly flush page cache and run garbage collection
                            page.flush_cache()
                            gc.collect()

                        # More frequent garbage collection for every 100 pages
                        if (page_num + 1) % 100 == 0:
                            gc.collect()

                    # Add the last record
                    if current_record:
                        records.append(current_record)

                    # Add last multi-page report if exists
                    if report_pages_buffer:
                        multi_report = self.report_parser.parse_multi_page_report(report_pages_buffer)
                        if multi_report:
                            records.append(multi_report)

                    # Log page processing statistics
                    logger.info(f"Page processing complete:")
                    logger.info(f"  - TABLE pages: {table_pages}")
                    logger.info(f"  - REPORT pages: {report_pages}")
                    logger.info(f"  - COVER pages: {cover_pages}")
                    logger.info(f"  - Total records extracted: {len(records)}")

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
