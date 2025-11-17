# FRT Parser Test Version - Usage Guide

## Overview

The test parser (`src/frt_parser_test.py`) is a limited version of the FRT parser that processes only the first 2000 pages by default. This allows you to:

- **Validate parsing logic** before running on the complete dataset
- **Preview output format** and data quality
- **Test column detection** and text extraction
- **Estimate processing time** for full parsing

## Quick Start

### Basic Usage (2000 pages)

```bash
# Use existing PDF, parse first 2000 pages
python src/frt_parser_test.py --skip-download
```

### Custom Page Limit

```bash
# Parse only first 500 pages (faster test)
python src/frt_parser_test.py --skip-download --max-pages 500

# Parse first 100 pages (quick validation)
python src/frt_parser_test.py --skip-download --max-pages 100
```

## Output Files

The test parser creates separate output files to avoid overwriting production data:

| File | Description |
|------|-------------|
| `data/frt_database_test.json` | Parsed firearm records (JSON array) |
| `data/parse_summary_test.json` | Parse statistics and metadata |
| `logs/frt_parser_test.log` | Detailed parsing log |

## What to Expect

### Processing Time

Approximate processing times (depends on hardware):

- **100 pages**: ~30-60 seconds
- **500 pages**: ~2-5 minutes
- **2000 pages**: ~8-15 minutes

Compare this to the full dataset which can take several hours.

### Output Format

The test output uses the same format as the production parser:

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

### Expected Record Count

From the first 2000 pages, you should expect:

- **Approximate records**: 15,000 - 25,000 entries
- **Classification mix**: Majority Non-Restricted, some Restricted/Prohibited
- **Page types**: Mix of TABLE, REPORT, and COVER pages

## Validation Checklist

After running the test parser, verify:

- [ ] Column detection succeeded (check logs for "Detected N columns")
- [ ] Output file created (`data/frt_database_test.json`)
- [ ] Summary file created (`data/parse_summary_test.json`)
- [ ] Records have valid FRNs (numeric, 5-7 characters)
- [ ] Classifications are standardized (Non-Restricted, Restricted, Prohibited)
- [ ] Notes field contains continuation text from multi-line rows
- [ ] OIC references extracted where present

## Sample Commands

### Quick validation (100 pages)
```bash
python src/frt_parser_test.py --skip-download --max-pages 100
```

### Standard test (2000 pages)
```bash
python src/frt_parser_test.py --skip-download
```

### Full validation with custom output
```bash
python src/frt_parser_test.py --skip-download --max-pages 2000 --output frt_validation.json
```

## Inspecting Results

### View summary statistics
```bash
cat data/parse_summary_test.json | python -m json.tool
```

### Count total records
```bash
cat data/frt_database_test.json | python -c "import sys, json; print(f'Total records: {len(json.load(sys.stdin))}')"
```

### View first 5 records
```bash
cat data/frt_database_test.json | python -c "import sys, json; import pprint; pprint.pprint(json.load(sys.stdin)[:5])"
```

### Classification breakdown
```bash
cat data/frt_database_test.json | python -c "
import sys, json
from collections import Counter
data = json.load(sys.stdin)
classes = Counter(r['class'] for r in data)
print('Classification Breakdown:')
for cls, count in classes.most_common():
    print(f'  {cls}: {count}')
"
```

## Troubleshooting

### No records extracted
**Cause**: Column detection failed or PDF structure unexpected
**Solution**: Check `logs/frt_parser_test.log` for column detection errors. Ensure PDF has expected headers: FRN, Make, Model, Manufacturer, Type, Action, Class, Notes.

### Low record count
**Cause**: FRN validation too strict or page classification excluding data pages
**Solution**: Review page classification statistics in logs. Adjust `max_pages` to include more data.

### Invalid classifications
**Cause**: Class column not properly detected or contains notes text
**Solution**: Verify column boundaries in logs. Check that Class column aligns with actual classification data in PDF.

## Differences from Production Parser

The test parser is **identical** to the production parser except:

1. **Page limit**: Only processes first `max_pages` (default 2000)
2. **Output file**: Uses `frt_database_test.json` instead of `frt_database.json`
3. **Summary file**: Uses `parse_summary_test.json` with additional test metadata
4. **Log file**: Uses `frt_parser_test.log` instead of `frt_parser.log`

All parsing logic, column detection, and validation rules are the same.

## Next Steps

After validating the test output:

1. **Review sample records** to ensure data quality
2. **Check classification distribution** matches expectations
3. **Verify multi-line notes** are properly concatenated
4. **Run full parser** if test results look good:
   ```bash
   python src/frt_parser.py --skip-download
   ```

## Command Reference

```bash
# Get help
python src/frt_parser_test.py --help

# Parse with existing PDF (recommended)
python src/frt_parser_test.py --skip-download [--max-pages N]

# Force download and parse
python src/frt_parser_test.py --force [--max-pages N]

# Custom output directory
python src/frt_parser_test.py --skip-download --data-dir /path/to/data

# Custom output filename
python src/frt_parser_test.py --skip-download --output my_test.json
```
