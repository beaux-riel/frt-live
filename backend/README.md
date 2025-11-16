# FRT-Live Backend: PDF Parser & Data Pipeline

Automated ingestion and parsing system for the RCMP Firearms Reference Table (FRT).

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
- Extracts FRN, Make, Model, Manufacturer, Type, Action, Class, and Notes

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

### Basic Parsing

Parse the FRT PDF and generate JSON database:

```bash
python src/frt_parser.py
```

This will:
1. Check for updates at the RCMP URL
2. Download the PDF if new version available
3. Parse all records
4. Output to `data/frt_database.json`

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
    "oic_references": []
  },
  {
    "frn": "789012",
    "make": "AR-15",
    "model": "Various",
    "manufacturer": "Various",
    "type": "Rifle",
    "action": "Semi-Auto",
    "class": "Prohibited",
    "notes": "Affected by OIC 2020-0001",
    "oic_references": ["OIC 2020-0001"]
  }
]
```

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
│   ├── frt_parser.py       # Main PDF parser
│   ├── diff_detector.py    # Change detection
│   ├── config.py           # Configuration
│   └── __init__.py
├── data/                   # Data storage (gitignored)
│   ├── frt_current.pdf
│   ├── frt_database.json
│   ├── frt_database_previous.json
│   ├── frt_changes.json
│   └── frt_metadata.json
├── logs/                   # Log files (gitignored)
│   └── frt_parser.log
├── requirements.txt
└── README.md
```

## Known Limitations

1. **PDF URL**: The actual RCMP FRT PDF URL may change. Update `FRT_PDF_URL` in config or via environment variable.

2. **Column Detection**: Parser assumes standard FRT table structure. Significant format changes by RCMP may require adjustments.

3. **Multi-line Rows**: Complex multi-line handling works for typical cases but may need refinement for unusual table structures.

4. **OIC Extraction**: Pattern matching for OIC references works for common formats but may miss non-standard notations.

## Troubleshooting

### "Failed to detect column boundaries"
- The PDF structure may have changed
- Check logs for details: `logs/frt_parser.log`
- Verify PDF has expected column headers

### "Error downloading PDF"
- Check internet connection
- Verify FRT_PDF_URL is correct
- RCMP website may be down or URL changed

### "No tables found on page"
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
