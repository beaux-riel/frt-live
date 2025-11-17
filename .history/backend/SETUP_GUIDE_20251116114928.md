# FRT PDF Parser Setup Guide

This guide helps you get the FRT parser working, especially if you encounter issues downloading the PDF automatically.

## Quick Start

### Method 1: Automatic Download (if it works)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/frt_parser.py
```

If you get a **403 Forbidden error** or the download fails, proceed to Method 2 or 3.

## Method 2: Find the PDF URL Automatically

Use the included utility to find PDF links on the RCMP page:

```bash
python find_pdf_url.py
```

This will scan the RCMP FRT page and show you any PDF download links it finds. Then use the URL with:

```bash
python src/frt_parser.py --url "https://example.com/path/to/frt.pdf"
```

Or set it as an environment variable:

```bash
export FRT_PDF_URL="https://example.com/path/to/frt.pdf"
python src/frt_parser.py
```

## Method 3: Manual Download (Most Reliable)

This is the recommended approach if automatic download fails:

### Step 1: Download the PDF Manually

1. Visit the RCMP FRT page in your browser:
   - https://rcmp.ca/en/firearms/firearms-reference-table

2. Find and click the PDF download link (usually labeled "Firearms Reference Table" or similar)

3. Save the PDF file

### Step 2: Place the PDF in the Correct Location

Copy or move the downloaded PDF to:

```bash
backend/data/frt_current.pdf
```

Create the data directory if it doesn't exist:

```bash
mkdir -p backend/data
mv ~/Downloads/FRT.pdf backend/data/frt_current.pdf
```

### Step 3: Run the Parser

Skip the download step and parse the local file:

```bash
cd backend
python src/frt_parser.py --skip-download
```

## Troubleshooting

### 403 Forbidden Error

**Problem**: The RCMP website is blocking automated downloads.

**Solutions**:
1. Use **Method 3** (manual download) - most reliable
2. Try finding the direct PDF URL with `python find_pdf_url.py`
3. The website may require authentication or have anti-bot protection

### "Received HTML page instead of PDF"

**Problem**: The URL points to a web page, not directly to a PDF.

**Solution**:
1. Visit the URL in your browser
2. Look for a "Download PDF" button or link
3. Right-click the link and "Copy Link Address"
4. Use that URL with `--url` parameter

### "No tables found on page"

**Problem**: The PDF structure is different than expected, or it's a scanned image PDF.

**Solutions**:
1. Verify the PDF is the official FRT (not a scanned copy)
2. Check the PDF has selectable text (not just images)
3. Open an issue on GitHub with details about the PDF

### "Failed to detect column boundaries"

**Problem**: The PDF table structure has changed.

**Solution**:
1. Open the PDF and verify it has the expected columns: FRN, Make, Model, etc.
2. If the structure changed significantly, the parser may need updates
3. Open an issue on GitHub with a sample from the PDF

## Command Line Options

```bash
python src/frt_parser.py --help
```

Available options:

- `--skip-download` - Skip download, use existing `data/frt_current.pdf`
- `--force` - Force re-download even if cached version exists
- `--url "URL"` - Use a custom PDF URL
- `--data-dir PATH` - Use custom data directory (default: `data`)
- `--output FILENAME` - Custom output filename (default: `frt_database.json`)

## Examples

### Parse existing local PDF

```bash
python src/frt_parser.py --skip-download
```

### Use custom PDF URL

```bash
python src/frt_parser.py --url "https://rcmp.ca/files/frt.pdf"
```

### Force re-download and parse

```bash
python src/frt_parser.py --force
```

### Use custom data directory

```bash
python src/frt_parser.py --data-dir /path/to/data --skip-download
```

## Updating the FRT Database

When a new FRT is released:

1. **Save the previous version** (for change detection):
   ```bash
   cp data/frt_database.json data/frt_database_previous.json
   ```

2. **Download the new PDF manually** or use automatic download:
   ```bash
   # Manual: download to data/frt_current.pdf
   # OR
   python src/frt_parser.py --force
   ```

3. **Run the parser**:
   ```bash
   python src/frt_parser.py --skip-download
   ```

4. **Detect changes**:
   ```bash
   python src/diff_detector.py
   ```

This will generate:
- `data/frt_changes.json` - Machine-readable changes
- `data/frt_changes_report.txt` - Human-readable report

## Getting Help

If you continue to have issues:

1. Check the log file: `logs/frt_parser.log`
2. Open an issue on GitHub with:
   - The error message
   - The log file contents
   - What you tried
3. Include the output of:
   ```bash
   python --version
   pip list
   ```

## Environment Variables

You can set these environment variables to configure the parser:

```bash
# Direct PDF URL
export FRT_PDF_URL="https://example.com/frt.pdf"

# Log level (DEBUG, INFO, WARNING, ERROR)
export LOG_LEVEL="DEBUG"
```

## Next Steps

Once you've successfully parsed the FRT:

- **Search**: Use `python example.py search` to search the database
- **Diff Detection**: Compare versions with `python src/diff_detector.py`
- **API**: Build the REST API (coming soon)
- **Mobile App**: Develop the Expo mobile app (coming soon)

## Important Notes

- The FRT PDF can be **very large** (100+ MB, 100,000+ pages)
- Parsing may take **several minutes to hours** depending on file size
- Ensure you have enough **disk space** (at least 500MB free)
- Use a **stable internet connection** for downloads
- Always **verify** classification info with official RCMP sources

## Legal Disclaimer

This tool is for informational purposes only. Always verify firearm classifications with official RCMP sources and legal counsel. The developers assume no liability for legal compliance issues.
