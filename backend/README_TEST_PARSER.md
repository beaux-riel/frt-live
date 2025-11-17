# FRT Parser - Test Version

## Quick Start

```bash
# Parse first 2000 pages (default)
python src/frt_parser_test.py --skip-download

# Parse fewer pages for quick validation
python src/frt_parser_test.py --skip-download --max-pages 500
```

## What This Does

The test parser (`src/frt_parser_test.py`) processes only the first N pages (default: 2000) of the FRT PDF, allowing you to:

✅ Validate parsing logic before running the full parser
✅ Preview output format and data quality
✅ Test column detection and extraction
✅ Estimate processing time

## Output Files

- `data/frt_database_test.json` - Parsed firearm records
- `data/parse_summary_test.json` - Statistics and metadata
- `logs/frt_parser_test.log` - Detailed parsing log

## Key Features

### 🔧 Identical Parsing Logic
Uses the same column detection and text extraction as the production parser (`src/frt_parser.py`).

### 📊 Progress Tracking
Shows progress bars and logs updates every 100 pages:
```
Processing pages (max 2000): 100%|██████████| 2000/2000
TEST: Processed 1000/2000 pages, 12,543 records so far
```

### 🎯 Configurable Page Limit
Adjust the number of pages to process:
```bash
--max-pages 100    # Quick test
--max-pages 500    # Medium validation
--max-pages 2000   # Standard test (default)
```

## Expected Results

For 2000 pages, expect:
- **Processing time**: ~8-15 minutes
- **Record count**: ~15,000-25,000 firearm entries
- **Page types**: Mix of TABLE, REPORT, and COVER pages

## Validation Steps

1. **Run the test parser**
   ```bash
   python src/frt_parser_test.py --skip-download
   ```

2. **Check the summary**
   ```bash
   cat data/parse_summary_test.json
   ```

3. **View sample records**
   ```bash
   python -c "import json; data=json.load(open('data/frt_database_test.json')); print(json.dumps(data[:3], indent=2))"
   ```

4. **Count records**
   ```bash
   python -c "import json; print(f'Total: {len(json.load(open(\"data/frt_database_test.json\")))}')"
   ```

## Full Documentation

See `docs/FRT_PARSER_TEST_GUIDE.md` for comprehensive usage instructions.

## Running the Full Parser

After validating with the test parser:
```bash
python src/frt_parser.py --skip-download
```

This processes all 100,000+ pages and creates `data/frt_database.json`.
