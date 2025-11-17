#!/usr/bin/env python3
"""
FRT Report Page Parser
Extracts structured data from individual FRT Report pages
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FRTReportParser:
    """
    Parser for individual FRT Report pages

    Each report page contains:
    - Header with FRN, Make, Model
    - Summary section with firearm details
    - Calibre/Shots/Barrel Length table
    - Notes section
    - Cross-references
    - Also Known As/Product Code
    """

    # Field labels commonly found in report pages
    FIELD_LABELS = {
        'Make:', 'Model:', 'Manufacturer:', 'Level:', 'Type:', 'Action:',
        'Country of Manufacturer:', 'Serial Numbering:', 'Legal Classification:',
        'Calibre:', 'Shots:', 'Barrel Length:', 'Year Dates:', 'Importer:'
    }

    # Section headers that indicate content boundaries
    SECTION_HEADERS = {
        'SUMMARY', 'NOTES', 'CROSS-REFERENCES', 'CROSS REFERENCES',
        'CALIBRE, SHOTS AND BARREL LENGTH', 'ALSO KNOWN AS',
        'PRODUCT CODE', 'YEAR DATES', 'IMPORTER'
    }

    def __init__(self):
        """Initialize the report parser"""
        pass

    def parse_report_page(self, page) -> Optional[Dict]:
        """
        Extract firearm data from a single report page

        Args:
            page: pdfplumber page object

        Returns:
            Dictionary with firearm data, or None if parsing fails
        """
        try:
            # Extract all text from the page
            text = page.extract_text()

            if not text:
                return None

            # Initialize record
            record = {
                'frn': '',
                'make': '',
                'model': '',
                'manufacturer': '',
                'type': '',
                'action': '',
                'class': 'Unknown',
                'notes': '',
                'oic_references': [],
                'country': '',
                'level': '',
                'serial_numbering': '',
                'calibre_variants': [],
                'product_codes': [],
                'cross_references': '',
                'multipage': False
            }

            # Extract FRN
            frn_match = re.search(r'Firearm Reference Number \(FRN\):\s*(\d+)', text)
            if frn_match:
                record['frn'] = frn_match.group(1).strip()
            else:
                # Try alternative format
                frn_match = re.search(r'FRN:\s*(\d+)', text)
                if frn_match:
                    record['frn'] = frn_match.group(1).strip()
                else:
                    logger.warning("Could not extract FRN from report page")
                    return None

            # Extract Summary section fields
            # Make
            make_match = re.search(r'Make:\s*([^\n]+)', text)
            if make_match:
                record['make'] = make_match.group(1).strip()

            # Model
            model_match = re.search(r'Model:\s*([^\n]+)', text)
            if model_match:
                record['model'] = model_match.group(1).strip()

            # Manufacturer
            mfg_match = re.search(r'Manufacturer:\s*([^\n]+)', text)
            if mfg_match:
                record['manufacturer'] = mfg_match.group(1).strip()

            # Level
            level_match = re.search(r'Level:\s*([^\n]+)', text)
            if level_match:
                record['level'] = level_match.group(1).strip()

            # Type
            type_match = re.search(r'Type:\s*([^\n]+)', text)
            if type_match:
                record['type'] = type_match.group(1).strip()

            # Action
            action_match = re.search(r'Action:\s*([^\n]+)', text)
            if action_match:
                record['action'] = action_match.group(1).strip()

            # Country of Manufacturer
            country_match = re.search(r'Country of Manufacturer:\s*([^\n]+)', text)
            if country_match:
                record['country'] = country_match.group(1).strip()

            # Serial Numbering
            serial_match = re.search(r'Serial Numbering:\s*([^\n]+)', text)
            if serial_match:
                record['serial_numbering'] = serial_match.group(1).strip()

            # Legal Classification
            class_match = re.search(r'Legal Classification:\s*([^\n]+)', text)
            if class_match:
                record['class'] = self._normalize_classification(class_match.group(1).strip())

            # Extract Notes section
            notes_match = re.search(r'Notes\s+(.*?)(?:Cross-References|Also Known As|Product Code|Importer|Year Dates|$)', text, re.DOTALL)
            if notes_match:
                notes_text = notes_match.group(1).strip()
                # Clean up notes (remove extra whitespace)
                notes_text = ' '.join(notes_text.split())
                record['notes'] = notes_text

            # Extract OIC references from notes
            if record['notes']:
                record['oic_references'] = self._extract_oic_references(record['notes'])

            # Extract calibre variants from table (if present)
            calibre_variants = self._extract_calibre_variants(text, page)
            if calibre_variants:
                record['calibre_variants'] = calibre_variants

            # Extract product codes
            product_codes = self._extract_product_codes(text)
            if product_codes:
                record['product_codes'] = product_codes

            # Extract cross-references
            cross_refs = self._extract_cross_references(text)
            record['cross_references'] = cross_refs

            return record

        except Exception as e:
            logger.error(f"Error parsing report page: {e}", exc_info=True)
            return None

    def _normalize_classification(self, class_value: str) -> str:
        """
        Normalize classification values

        Args:
            class_value: Raw classification string

        Returns:
            Standardized classification
        """
        if not class_value:
            return "Unknown"

        class_upper = class_value.upper()

        # Standard mappings
        if 'NON-RESTRICTED' in class_upper or 'NON RESTRICTED' in class_upper:
            return 'Non-Restricted'
        elif 'RESTRICTED' in class_upper and 'NON' not in class_upper:
            return 'Restricted'
        elif 'PROHIBITED' in class_upper:
            return 'Prohibited'
        elif re.search(r'12\(\d\)', class_upper):  # 12(2), 12(3), etc.
            return 'Prohibited'

        # Return original if no match
        return class_value

    def _extract_oic_references(self, text: str) -> List[str]:
        """
        Extract OIC (Order in Council) references from text

        Args:
            text: Text to search

        Returns:
            List of OIC references
        """
        if not text:
            return []

        # Pattern to match OIC references (e.g., "OIC 2020-123", "OIC #2020-0001")
        pattern = r'OIC\s*#?\s*(\d{4}-\d{3,4})'
        matches = re.findall(pattern, text, re.IGNORECASE)

        return [f"OIC {match}" for match in matches]

    def _find_frn_in_page(self, page) -> Optional[str]:
        """
        Search entire page for FRN (more robust than header-only search)

        Args:
            page: pdfplumber page object

        Returns:
            FRN string if found, None otherwise
        """
        text = page.extract_text()
        if not text:
            return None

        # Try primary format first
        frn_match = re.search(r'Firearm Reference Number \(FRN\):\s*(\d+)', text)
        if frn_match:
            return frn_match.group(1).strip()

        # Try alternative formats
        patterns = [
            r'FRN:\s*(\d+)',
            r'FRN\s+(\d{6})',
            r'Firearm Reference Number.*?(\d{6})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _is_continuation_page(self, page, expected_frn: str) -> bool:
        """
        Detect if page continues previous report

        Args:
            page: pdfplumber page object
            expected_frn: FRN to validate against

        Returns:
            True if page is a continuation of the same report
        """
        text = page.extract_text()
        if not text:
            return False

        # Check for FRN match
        page_frn = self._find_frn_in_page(page)

        # If FRN matches, this is a continuation page
        # (FRT reports can have headers on all pages)
        if page_frn and page_frn == expected_frn:
            return True

        return False

    def _extract_section_content(self, text: str, section_header: str, next_sections: List[str] = None) -> str:
        """
        Extract all text under a section header until next section

        Args:
            text: Full page text
            section_header: Header to find (e.g., "Make", "Model", "Notes")
            next_sections: List of possible next section headers

        Returns:
            Extracted section content
        """
        if not next_sections:
            next_sections = list(self.SECTION_HEADERS) + list(self.FIELD_LABELS)

        # Build regex pattern to find section and content until next section
        # Handle both "Section:" and "Section" formats
        section_patterns = [
            section_header + r'\s*',
            section_header + r':\s*'
        ]

        for pattern in section_patterns:
            # Create next section pattern (match any of the possible next sections)
            next_pattern = '|'.join(re.escape(s) for s in next_sections if s != section_header)

            if next_pattern:
                match = re.search(
                    rf'{pattern}(.*?)(?:{next_pattern}|$)',
                    text,
                    re.DOTALL | re.IGNORECASE
                )
            else:
                match = re.search(rf'{pattern}(.*?)$', text, re.DOTALL | re.IGNORECASE)

            if match:
                content = match.group(1).strip()
                # Clean up extra whitespace
                content = ' '.join(content.split())
                return content

        return ''

    def _extract_product_codes(self, text: str) -> List[str]:
        """
        Extract product codes from "Also Known As/Product Code" section

        Args:
            text: Page text

        Returns:
            List of product codes
        """
        product_codes = []

        # Find "Also Known As" or "Product Code" section
        patterns = [
            r'Also Known As[:\s]+(.*?)(?:Year Dates|Importer|Cross-References|$)',
            r'Product Code[:\s]+(.*?)(?:Year Dates|Importer|Cross-References|$)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                section_text = match.group(1).strip()
                # Split by newlines to get individual codes
                codes = [line.strip() for line in section_text.split('\n') if line.strip()]
                product_codes.extend(codes)

        return product_codes

    def _extract_cross_references(self, text: str) -> str:
        """
        Extract cross-references section

        Args:
            text: Page text

        Returns:
            Cross-references content
        """
        patterns = [
            r'Cross-References[:\s]+(.*?)(?:Also Known As|Product Code|Year Dates|Importer|$)',
            r'Cross References[:\s]+(.*?)(?:Also Known As|Product Code|Year Dates|Importer|$)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # Clean up
                content = ' '.join(content.split())
                return content if content else 'No Data'

        return 'No Data'

    def _extract_calibre_variants(self, text: str, page) -> List[Dict]:
        """
        Extract calibre variant information from the Calibre/Shots/Barrel Length table

        Args:
            text: Page text
            page: pdfplumber page object

        Returns:
            List of calibre variant dictionaries
        """
        variants = []

        try:
            # Try to extract table data using pdfplumber
            tables = page.extract_tables()

            if not tables:
                return variants

            # Look for the calibre/barrel table
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Check if this is the calibre table by looking at headers
                header_row = [str(cell).upper() if cell else '' for cell in table[0]]

                # Look for expected headers
                has_frn = any('FRN' in h for h in header_row)
                has_calibre = any('CALIBRE' in h or 'CALIBER' in h for h in header_row)
                has_barrel = any('BARREL' in h for h in header_row)

                if has_frn and (has_calibre or has_barrel):
                    # This is likely the calibre table
                    # Extract data rows
                    for row in table[1:]:
                        if not row or all(not cell for cell in row):
                            continue

                        # Try to parse row data
                        variant = {}

                        # Map by position (common layout)
                        if len(row) >= 3:
                            # FRN, Calibre, Shots, Barrel, Classification, etc.
                            for i, header in enumerate(header_row):
                                if i < len(row) and row[i]:
                                    variant[header.lower()] = str(row[i]).strip()

                        if variant:
                            variants.append(variant)

        except Exception as e:
            logger.debug(f"Could not extract calibre variants: {e}")

        return variants

    def parse_multi_page_report(self, pages: List) -> Optional[Dict]:
        """
        Parse a multi-page report (some firearms span multiple pages)

        Args:
            pages: List of pdfplumber page objects for a single firearm

        Returns:
            Combined firearm data dictionary
        """
        if not pages:
            return None

        # Parse first page (contains main data)
        record = self.parse_report_page(pages[0])

        if not record:
            return None

        # Mark as multipage if more than one page
        if len(pages) > 1:
            record['multipage'] = True
            record['page_count'] = len(pages)

        # If there are additional pages, extract continuation data
        for page_idx, page in enumerate(pages[1:], start=2):
            text = page.extract_text()
            if not text:
                logger.debug(f"Page {page_idx} of FRN {record['frn']} has no text")
                continue

            # Validate this is a continuation page
            if not self._is_continuation_page(page, record['frn']):
                logger.warning(f"Page {page_idx} doesn't match FRN {record['frn']}, skipping")
                continue

            logger.debug(f"Processing continuation page {page_idx} for FRN {record['frn']}")

            # Extract extended Make description if present
            make_content = self._extract_section_content(text, 'Make')
            if make_content and make_content not in record.get('notes', ''):
                # Append to notes with label
                record['notes'] += f" Make - {make_content}"

            # Extract extended Model description if present
            model_content = self._extract_section_content(text, 'Model')
            if model_content and model_content not in record.get('notes', ''):
                record['notes'] += f" Model - {model_content}"

            # Extract extended Manufacturer description if present
            manufacturer_content = self._extract_section_content(text, 'Manufacturer')
            if manufacturer_content and manufacturer_content not in record.get('notes', ''):
                record['notes'] += f" Manufacturer - {manufacturer_content}"

            # Extract Action description if present
            action_content = self._extract_section_content(text, 'Action')
            if action_content and action_content not in record.get('notes', ''):
                record['notes'] += f" Action - {action_content}"

            # Extract Serial Number description if present
            serial_content = self._extract_section_content(text, 'Serial Number')
            if serial_content and serial_content not in record.get('notes', ''):
                record['notes'] += f" Serial Number - {serial_content}"

            # Extract Calibre description if present
            calibre_content = self._extract_section_content(text, 'Calibre')
            if calibre_content and calibre_content not in record.get('notes', ''):
                record['notes'] += f" Calibre - {calibre_content}"

            # Extract Shots description if present
            shots_content = self._extract_section_content(text, 'Shots')
            if shots_content and shots_content not in record.get('notes', ''):
                record['notes'] += f" Shots - {shots_content}"

            # Extract additional product codes
            additional_codes = self._extract_product_codes(text)
            if additional_codes:
                # Avoid duplicates
                for code in additional_codes:
                    if code not in record.get('product_codes', []):
                        record['product_codes'].append(code)

            # Extract additional calibre variants
            variants = self._extract_calibre_variants(text, page)
            if variants:
                record['calibre_variants'].extend(variants)

            # Update cross-references if found
            cross_refs = self._extract_cross_references(text)
            if cross_refs and cross_refs != 'No Data':
                record['cross_references'] = cross_refs

        # Clean up notes (remove excessive whitespace)
        if record.get('notes'):
            record['notes'] = ' '.join(record['notes'].split())

        return record
