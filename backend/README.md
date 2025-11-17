# FRT-Live Backend: PDF Parser & Data Pipeline

Automated ingestion and parsing system for the RCMP Firearms Reference Table (FRT).

> **⚠️ IMPORTANT**: If you get a **403 Forbidden** error when downloading the PDF, see the [Setup Guide](SETUP_GUIDE.md) for manual download instructions. The RCMP website may block automated downloads.

## Overview

This backend system provides:

- **Automated PDF Download**: Monitors RCMP website for FRT updates using Last-Modified headers
- **Intelligent Parsing**: Extracts 100,000+ firearm records from complex multi-page tabular PDFs
- **Change Detection**: Identifies additions, removals, and critical classification changes between versions
- **JSON API-Ready Output**: Generates clean, structured JSON for downstream consumption

## Features

### Smart PDF Ingestion
- Checks for updates before downloading (via HTTP Last-Modified headers)
- Handles massive PDFs (100+ MB, 100,000+ pages) efficiently
- Caches downloads to avoid redundant transfers

### Advanced Table Extraction
- Automatically detects column boundaries from PDF structure
- Handles multi-line rows that span across pages
- **NEW**: Supports multipage firearm records (detailed report pages spanning 2-3+ pages)
- Intelligent page classification (TABLE, REPORT, COVER page types)
- Extracts FRN, Make, Model, Manufacturer, Type, Action, Class, Notes, Product Codes, and more

### Data Sanitization
- Standardizes classification values (Non-Restricted, Restricted, Prohibited)
- Extracts OIC (Order in Council) references from notes
- Validates FRN (Firearm Reference Number) formats

### Change Detection & Alerts
- Compares database versions to identify diffs
- Tracks critical classification changes (Non-Restricted → Prohibited)
- Generates detailed change reports for compliance monitoring

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir -p data logs
```

## Usage

### Quick Start (Recommended for 403 Errors)

If automatic download fails, manually download the PDF and parse it:

```bash
# 1. Manually download FRT PDF from https://rcmp.ca/en/firearms/firearms-reference-table
# 2. Save it to backend/data/frt_current.pdf
# 3. Run parser:
python src/frt_parser.py --skip-download
```

**See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting.**

### Basic Parsing (Automatic Download)

Parse the FRT PDF and generate JSON database:

```bash
python src/frt_parser.py
```

This will:
1. Check for updates at the RCMP URL
2. Download the PDF if new version available
3. Parse all records
4. Output to `data/frt_database.json`

### Find PDF URL

Use the helper utility to find PDF links on the RCMP page:

```bash
python find_pdf_url.py
```

Then use the URL it finds:

```bash
python src/frt_parser.py --url "https://example.com/frt.pdf"
```

### Force Re-download

Force download even if cached version exists:

```bash
python src/frt_parser.py --force
```

### Custom Output Location

Specify custom data directory and output file:

```bash
python src/frt_parser.py --data-dir /path/to/data --output my_frt.json
```

### Change Detection

After updating the database, detect changes from previous version:

```bash
python src/diff_detector.py
```

This generates:
- `data/frt_changes.json` - Machine-readable change data
- `data/frt_changes_report.txt` - Human-readable summary

### Example Workflow

```bash
# Initial parse
python src/frt_parser.py

# Save current version as "previous" for comparison
cp data/frt_database.json data/frt_database_previous.json

# Wait for new FRT release...

# Parse new version
python src/frt_parser.py

# Detect changes
python src/diff_detector.py
```

## Configuration

### Environment Variables

Set the FRT PDF URL via environment variable:

```bash
export FRT_PDF_URL="https://www.rcmp-grc.gc.ca/path/to/frt.pdf"
```

### Log Level

Control logging verbosity:

```bash
export LOG_LEVEL="DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR
```

## Output Format

### FRT Database JSON

```json
[
  {
    "frn": "123456",
    "make": "Remington",
    "model": "870",
    "manufacturer": "Remington Arms Company",
    "type": "Shotgun",
    "action": "Pump",
    "class": "Non-Restricted",
    "notes": "Standard hunting configuration",
    "oic_references": [],
    "product_codes": [],
    "cross_references": "No Data",
    "multipage": false
  },
  {
    "frn": "789012",
    "make": "AR-15",
    "model": "Various",
    "manufacturer": "Various",
    "type": "Rifle",
    "action": "Semi-Auto",
    "class": "Prohibited",
    "notes": "Detailed specifications extracted from multiple report pages...",
    "oic_references": ["OIC 2020-0001"],
    "product_codes": ["AR15-A", "AR15-B", "M16-COPY"],
    "cross_references": "See FRN 123457",
    "calibre_variants": [
      {"frn": "789012-1", "calibre": "5.56 NATO", "shots": "30"}
    ],
    "multipage": true,
    "page_count": 3
  }
]
```

**New Fields (v2.0):**
- `product_codes`: Array of "Also Known As" product codes/names
- `cross_references`: Related FRN references
- `calibre_variants`: Detailed calibre/barrel length variants
- `multipage`: Boolean indicating if extracted from multiple pages
- `page_count`: Number of pages the record spanned (if multipage)

### Changes JSON

```json
{
  "added": [...],
  "removed": [...],
  "modified": [...],
  "classification_changed": [
    {
      "frn": "123456",
      "make": "Example",
      "model": "Model X",
      "old_class": "Non-Restricted",
      "new_class": "Prohibited",
      "oic_references": ["OIC 2025-0042"]
    }
  ],
  "metadata": {
    "detection_date": "2025-03-07T12:00:00",
    "current_count": 105234,
    "previous_count": 105055,
    "added_count": 179,
    "removed_count": 0,
    "modified_count": 179,
    "classification_changes": 179
  }
}
```

## Architecture

```
backend/
├── src/
│   ├── frt_parser.py          # Main PDF parser with multipage support
│   ├── frt_report_parser.py   # Detailed report page parser
│   ├── page_classifier.py     # Page type detection (TABLE/REPORT/COVER)
│   ├── diff_detector.py       # Change detection
│   ├── config.py              # Configuration
│   └── __init__.py
├── data/                      # Data storage (gitignored)
│   ├── frt_current.pdf
│   ├── frt_database.json
│   ├── frt_database_previous.json
│   ├── frt_changes.json
│   └── frt_metadata.json
├── logs/                      # Log files (gitignored)
│   └── frt_parser.log
├── tests/                     # Test suite
│   ├── test_multipage_extraction.py
│   ├── test_report_parser.py
│   └── validate_frn_152726.py
├── requirements.txt
└── README.md
```

### Parsing Strategy

The parser uses a **multi-strategy approach** to handle different page layouts:

1. **Page Classification**: Each page is classified as TABLE, REPORT, or COVER
   - TABLE pages contain multiple firearm records in columnar format
   - REPORT pages contain detailed information for a single firearm (may span 2-3+ pages)
   - COVER pages are skipped

2. **Column-Based Extraction** (TABLE pages):
   - Detects column boundaries from header row
   - Assigns words to columns based on center-point detection
   - Reconstructs rows from sequential words

3. **Multipage Report Buffering** (REPORT pages):
   - Tracks continuation pages by FRN
   - Buffers all pages for the same FRN
   - Stitches content from multiple pages into single record
   - Extracts extended descriptions, product codes, calibre variants

## Multipage Record Support (v2.0)

The parser now **fully supports multipage firearm records**. Some firearms in the FRT have detailed specifications that span 2-3+ pages.

### How It Works

1. **Automatic Detection**: Pages with the same FRN are automatically grouped together
2. **Continuation Tracking**: Each continuation page is validated to ensure it belongs to the same firearm
3. **Content Merging**: Information from all pages is intelligently merged:
   - Extended Make/Model/Manufacturer descriptions
   - Product codes and aliases
   - Calibre variants and specifications
   - Cross-references

### Example: FRN 152726

This firearm spans 3 pages in the PDF:
- **Page 1**: Basic summary (Make, Model, Type, Class)
- **Page 2**: Detailed descriptions of Make, Model, Manufacturer, Action, Serial Number, Calibre, Shots
- **Page 3**: Product codes (12 different aliases)

The parser automatically extracts all this information and combines it into a single comprehensive record.

### Testing Multipage Extraction

```bash
# Validate multipage extraction for FRN 152726
python tests/validate_frn_152726.py

# Run full test suite
python -m pytest tests/test_multipage_extraction.py -v
```

## Known Limitations

1. **PDF URL**: The actual RCMP FRT PDF URL may change. Update `FRT_PDF_URL` in config or via environment variable.

2. **Column Detection**: Parser assumes standard FRT table structure. Significant format changes by RCMP may require adjustments.

3. **Calibre Variant Tables**: Table extraction within report pages may miss complex nested tables (depends on PDF structure).

4. **OIC Extraction**: Pattern matching for OIC references works for common formats but may miss non-standard notations.

## Troubleshooting

**📖 For detailed troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

### Common Issues

#### 403 Forbidden Error
The RCMP website is blocking automated downloads. **Solution**: Manually download the PDF.

See [SETUP_GUIDE.md](SETUP_GUIDE.md) → Method 3: Manual Download

#### "Received HTML page instead of PDF"
The URL points to a webpage, not directly to a PDF. **Solution**: Find the actual PDF download link.

See [SETUP_GUIDE.md](SETUP_GUIDE.md) → Method 2: Find the PDF URL

#### "Failed to detect column boundaries"
- The PDF structure may have changed
- Check logs for details: `logs/frt_parser.log`
- Verify PDF has expected column headers

#### "No tables found on page"
- PDF may use different structure
- Check if PDF is text-based (not scanned image)
- May need OCR if PDF is image-based

## Next Steps

- **API Server**: Build FastAPI REST endpoint to serve JSON data
- **Database**: Migrate to PostgreSQL for better query performance
- **Scheduler**: Add cron job for automatic daily checks
- **Webhooks**: Send notifications on classification changes
- **Search**: Implement fuzzy search for make/model lookup

## License

MIT License - See main repository for details

## Contributing

This is part of the larger FRT-Live project. See main repository for contribution guidelines.

## Disclaimer

This tool is for informational purposes only. Always verify firearm classifications with official RCMP sources and legal counsel. The developers assume no liability for legal compliance issues.
