"""
Configuration for FRT-Live Parser
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
LOGS_DIR = BASE_DIR / 'logs'

# RCMP FRT URL
# NOTE: This is the FRT information page. The actual PDF link is on this page.
# The RCMP provides the FRT at their website, but the exact PDF URL may change.
# Main page: https://rcmp.ca/en/firearms/firearms-reference-table
# You need to find the direct PDF link from this page.
# To use a direct PDF URL, set the FRT_PDF_URL environment variable.
FRT_PDF_URL = os.getenv(
    'FRT_PDF_URL',
    'https://rcmp.ca/en/firearms/firearms-reference-table'
)

# File names
FRT_CURRENT_PDF = 'frt_current.pdf'
FRT_PREVIOUS_PDF = 'frt_previous.pdf'
FRT_DATABASE_JSON = 'frt_database.json'
FRT_PREVIOUS_JSON = 'frt_database_previous.json'
FRT_METADATA_JSON = 'frt_metadata.json'
FRT_CHANGES_JSON = 'frt_changes.json'

# Parser settings
COLUMN_HEADERS = ['FRN', 'Make', 'Model', 'Manufacturer', 'Type', 'Action', 'Class', 'Notes']

# Classification mappings
CLASSIFICATION_MAP = {
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

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# HTTP settings
REQUEST_TIMEOUT = 30
DOWNLOAD_CHUNK_SIZE = 8192
