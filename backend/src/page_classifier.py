"""
Page Classification Module for FRT PDF Parser
Detects and classifies different page layouts in the FRT PDF
"""

import re
import logging
from typing import Dict, List, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class PageClassifier:
    """
    Classifies FRT PDF pages into different layout types

    Page Types:
    - TABLE: Multi-record tabular data pages
    - REPORT: Single-record detailed report pages
    - COVER: Cover/title pages
    - UNKNOWN: Unclassifiable pages
    """

    # Section headers commonly found in detailed report pages
    REPORT_SECTION_HEADERS = {
        'SUMMARY', 'NOTES', 'CROSS-REFERENCES', 'CROSS REFERENCES',
        'CALIBRE', 'SHOTS', 'BARREL LENGTH', 'ALSO KNOWN AS',
        'PRODUCT CODE', 'CANADIAN LAW COMMENTS'
    }

    # Keywords that indicate a detailed report page
    REPORT_KEYWORDS = {
        'FRT Report', 'Firearm Reference Number (FRN)',
        'Legal Classification:', 'Country of Manufacturer:',
        'Serial Numbering:'
    }

    def __init__(self):
        """Initialize the page classifier"""
        pass

    def classify(self, page) -> str:
        """
        Classify a PDF page into a layout type

        Args:
            page: pdfplumber page object

        Returns:
            Page type: 'TABLE', 'REPORT', 'COVER', or 'UNKNOWN'
        """
        try:
            # Extract page metrics
            metrics = self._extract_metrics(page)

            # Decision tree for classification

            # Check for cover page (minimal text, large font)
            if metrics['word_count'] < 50 and metrics['has_large_fonts']:
                return 'COVER'

            # Check for detailed report page
            if self._is_report_page(metrics):
                return 'REPORT'

            # Check for table page
            if self._is_table_page(metrics):
                return 'TABLE'

            return 'UNKNOWN'

        except Exception as e:
            logger.warning(f"Error classifying page: {e}")
            return 'UNKNOWN'

    def _extract_metrics(self, page) -> Dict:
        """
        Extract metrics from a page for classification

        Args:
            page: pdfplumber page object

        Returns:
            Dictionary of metrics
        """
        # Extract words with positions
        words = page.extract_words(x_tolerance=3, y_tolerance=3)

        if not words:
            return {
                'word_count': 0,
                'has_large_fonts': False,
                'has_section_headers': False,
                'has_report_keywords': False,
                'num_columns': 0,
                'row_count': 0,
                'text_density': 0,
                'has_lines': False
            }

        # Word count
        word_count = len(words)

        # Check for large fonts (indicating headers/titles)
        has_large_fonts = False
        if hasattr(words[0], '__getitem__') and 'size' in words[0]:
            font_sizes = [w.get('size', 10) for w in words]
            max_font_size = max(font_sizes) if font_sizes else 10
            has_large_fonts = max_font_size > 18

        # Extract all text for keyword search
        all_text = ' '.join([w['text'] for w in words])

        # Check for section headers
        has_section_headers = any(
            header in all_text.upper()
            for header in self.REPORT_SECTION_HEADERS
        )

        # Check for report keywords
        has_report_keywords = any(
            keyword in all_text
            for keyword in self.REPORT_KEYWORDS
        )

        # Detect column structure using x-position histogram
        x_positions = [w['x0'] for w in words]
        num_columns = self._count_column_peaks(x_positions)

        # Count approximate rows by grouping y-positions
        y_positions = [round(w['top'], 0) for w in words]
        row_count = len(set(y_positions))

        # Calculate text density
        text_area = sum((w['x1'] - w['x0']) * (w['bottom'] - w['top']) for w in words)
        page_area = page.width * page.height
        text_density = text_area / page_area if page_area > 0 else 0

        # Check for lines (table indicators)
        has_lines = len(page.lines) > 5

        return {
            'word_count': word_count,
            'has_large_fonts': has_large_fonts,
            'has_section_headers': has_section_headers,
            'has_report_keywords': has_report_keywords,
            'num_columns': num_columns,
            'row_count': row_count,
            'text_density': text_density,
            'has_lines': has_lines,
            'all_text': all_text
        }

    def _count_column_peaks(self, x_positions: List[float]) -> int:
        """
        Count the number of column peaks in x-position distribution

        Args:
            x_positions: List of x-coordinates

        Returns:
            Estimated number of columns
        """
        if not x_positions:
            return 0

        # Create histogram of x-positions
        # Round to nearest 10 pixels for grouping
        rounded_positions = [round(x / 10) * 10 for x in x_positions]
        position_counts = Counter(rounded_positions)

        # Find peaks (positions with high frequency)
        if not position_counts:
            return 0

        mean_count = sum(position_counts.values()) / len(position_counts)
        peaks = [pos for pos, count in position_counts.items() if count > mean_count * 1.5]

        return len(peaks)

    def _is_continuation_report(self, metrics: Dict) -> bool:
        """
        Detect report continuation pages (pages 2+ of a multi-page report)

        Args:
            metrics: Page metrics dictionary

        Returns:
            True if this appears to be a continuation page
        """
        all_text = metrics.get('all_text', '')

        # Has section headers but missing primary report header
        has_continuation_headers = any(
            header in all_text.upper()
            for header in ['MAKE', 'MODEL', 'MANUFACTURER', 'ACTION',
                          'SERIAL NUMBER', 'CALIBRE', 'SHOTS',
                          'ALSO KNOWN AS', 'PRODUCT CODE']
        )

        missing_report_header = 'FRT Report' not in all_text

        # Has FRN reference but not in header format
        has_frn_reference = bool(re.search(r'\bFRN[:\s]*\d{6}', all_text))

        # Continuation pages have narrative text (not columnar)
        has_narrative_text = metrics['text_density'] > 0.3 and metrics['num_columns'] < 3

        # If has section headers + narrative text + (FRN or missing header), likely continuation
        if has_continuation_headers and has_narrative_text:
            return True

        # Strong signal: has FRN + section headers + no "FRT Report" header
        if has_frn_reference and has_continuation_headers and missing_report_header:
            return True

        return False

    def _is_report_page(self, metrics: Dict) -> bool:
        """
        Determine if page is a detailed report page

        Args:
            metrics: Page metrics dictionary

        Returns:
            True if page is a detailed report
        """
        # Strong indicators
        if metrics['has_report_keywords']:
            return True

        # Check if this is a continuation page
        if self._is_continuation_report(metrics):
            return True

        # Multiple section headers is a strong indicator
        if metrics['has_section_headers']:
            # Count how many section headers are present
            section_count = sum(
                1 for header in self.REPORT_SECTION_HEADERS
                if header in metrics.get('all_text', '').upper()
            )
            if section_count >= 2:  # At least 2 sections
                return True

        # High text density + few columns suggests narrative text
        if metrics['text_density'] > 0.4 and metrics['num_columns'] < 3:
            return True

        return False

    def _is_table_page(self, metrics: Dict) -> bool:
        """
        Determine if page is a table page

        Args:
            metrics: Page metrics dictionary

        Returns:
            True if page is a table
        """
        # Strong indicators of table structure

        # Multiple columns (at least 4 for FRT tables)
        if metrics['num_columns'] >= 4:
            return True

        # Lines + moderate column count
        if metrics['has_lines'] and metrics['num_columns'] >= 3:
            return True

        # Many rows + multiple columns
        if metrics['row_count'] > 20 and metrics['num_columns'] >= 3:
            return True

        return False


def classify_pages(pdf, max_pages: int = None) -> Dict[int, str]:
    """
    Classify all pages in a PDF

    Args:
        pdf: pdfplumber PDF object
        max_pages: Maximum number of pages to classify (None for all)

    Returns:
        Dictionary mapping page numbers to page types
    """
    classifier = PageClassifier()
    page_types = {}

    pages_to_process = pdf.pages[:max_pages] if max_pages else pdf.pages

    for page in pages_to_process:
        page_num = page.page_number
        page_type = classifier.classify(page)
        page_types[page_num] = page_type
        logger.debug(f"Page {page_num}: {page_type}")

    # Log summary
    type_counts = Counter(page_types.values())
    logger.info(f"Page classification summary: {dict(type_counts)}")

    return page_types
