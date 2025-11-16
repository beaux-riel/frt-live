# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FRT-Live Backend is a Python-based PDF parser and data pipeline for the RCMP Firearms Reference Table (FRT). It automates downloading, parsing, and change detection for 100,000+ firearm records from complex multi-page tabular PDFs.

## Common Commands

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir -p data logs
```

### Running the Parser

```bash
# Automatic download and parse
python src/frt_parser.py

# Skip download (use existing PDF at data/frt_current.pdf)
python src/frt_parser.py --skip-download

# Force re-download even if cached
python src/frt_parser.py --force

# Use custom PDF URL
python src/frt_parser.py --url "https://example.com/frt.pdf"

# Custom data directory and output
python src/frt_parser.py --data-dir /path/to/data --output my_frt.json
```

### Change Detection

```bash
# Detect changes between versions
python src/diff_detector.py

# Manual workflow for version comparison
cp data/frt_database.json data/frt_database_previous.json
python src/frt_parser.py
python src/diff_detector.py
```

### Utilities

```bash
# Find PDF URL on RCMP website
python find_pdf_url.py

# Run example usage demonstrations
python example.py
```

### Testing Individual Modules

```bash
# Test parser module
python -c "from src.frt_parser import FRTParser; p = FRTParser(); print('Parser OK')"

# Test diff detector
python -c "from src.diff_detector import FRTDiffDetector; d = FRTDiffDetector(); print('Diff OK')"
```

## Architecture

### Core Components

**src/frt_parser.py** (FRTParser class)
- Main PDF parsing engine using pdfplumber
- Column-based text extraction (NOT table extraction)
- Words are assigned to columns based on center-point detection
- Handles multi-line rows that span across pages
- Downloads PDFs with browser-like headers to avoid 403 errors
- Uses Last-Modified headers for update detection
- Outputs to `data/frt_database.json`

**src/diff_detector.py** (FRTDiffDetector class)
- Compares FRT database versions (current vs previous)
- Detects additions, removals, and modifications
- Identifies critical classification changes (e.g., Non-Restricted → Prohibited)
- Extracts OIC (Order in Council) references
- Outputs to `data/frt_changes.json` and `data/frt_changes_report.txt`

**src/config.py**
- Centralized configuration
- Environment variable support (FRT_PDF_URL, LOG_LEVEL)
- Classification mappings (NR → Non-Restricted, etc.)
- Column headers and directory paths

### Key Parsing Strategy

The parser uses **column-based text extraction** rather than table extraction:
1. Detects column boundaries from header positions on first page
2. Assigns words to columns based on their center point (x-coordinate)
3. Reconstructs rows from sequential words in each column
4. This approach is more reliable than table extraction for complex multi-page PDFs

### Data Flow

```
RCMP Website → download_pdf() → data/frt_current.pdf
                                        ↓
                                 parse_pdf()
                                        ↓
                            Column boundary detection
                                        ↓
                            Word-to-column assignment
                                        ↓
                              Row reconstruction
                                        ↓
                           data/frt_database.json
                                        ↓
                              diff_detector.py
                                        ↓
                          data/frt_changes.json
```

### Directory Structure

```
backend/
├── src/                        # Source code modules
│   ├── frt_parser.py          # Main PDF parser
│   ├── diff_detector.py       # Change detection
│   ├── config.py              # Configuration
│   └── __init__.py
├── data/                      # Generated data (gitignored)
│   ├── frt_current.pdf
│   ├── frt_database.json
│   ├── frt_database_previous.json
│   ├── frt_changes.json
│   └── frt_metadata.json
├── logs/                      # Log files (gitignored)
│   └── frt_parser.log
├── venv/                      # Virtual environment (gitignored)
├── requirements.txt           # Python dependencies
├── example.py                 # Usage examples
├── find_pdf_url.py           # PDF URL finder utility
└── README.md                 # Documentation
```

## Configuration

### Environment Variables

```bash
# Direct PDF URL (overrides default)
export FRT_PDF_URL="https://rcmp.ca/sites/default/files/dam/frt-1103.pdf"

# Logging level
export LOG_LEVEL="DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR
```

### Output Format

**frt_database.json**: Array of firearm records
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
  }
]
```

**frt_changes.json**: Change detection results
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
    "previous_count": 105055
  }
}
```

## Common Issues

### 403 Forbidden Error
The RCMP website blocks automated downloads. **Solution**: Manually download PDF to `data/frt_current.pdf` and use `--skip-download`.

### HTML Instead of PDF
The URL points to a webpage. **Solution**: Use `find_pdf_url.py` to locate the direct PDF link.

### Column Detection Failures
PDF structure changed significantly. **Solution**: Check `logs/frt_parser.log` and verify PDF has expected column headers (FRN, Make, Model, Manufacturer, Type, Action, Class, Notes).

## Dependencies

- **pdfplumber**: PDF text extraction
- **requests**: HTTP downloads with browser headers
- **beautifulsoup4**: HTML parsing (for find_pdf_url.py)
- **python-dateutil**: Last-Modified header parsing
- **tqdm**: Progress bars

## Logging

All operations log to both console and `logs/frt_parser.log`. Use LOG_LEVEL environment variable to control verbosity.
