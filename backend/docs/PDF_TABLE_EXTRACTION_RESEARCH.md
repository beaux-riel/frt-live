# PDF Table Extraction Library Research

## Executive Summary

This research analyzes alternative Python libraries for extracting tables from complex PDFs, specifically for the RCMP Firearms Reference Table (FRT) parser which processes multi-page tabular PDFs with 100,000+ records. The FRT PDF has unique challenges:
- Tables spanning multiple pages
- Multi-line cell content
- Complex nested structures
- Rows that continue across page boundaries

## Current Implementation Analysis

**Current Tool:** pdfplumber (column-based extraction)
**Approach:** Custom column boundary detection with center-point word assignment
**File:** `/Users/beauxwalton/frt-live/frt-live/backend/src/frt_parser.py`

### Current Strategy
1. Detects column boundaries from header positions on first page
2. Assigns words to columns based on their center point (x-coordinate)
3. Reconstructs rows from sequential words in each column
4. More reliable than pdfplumber's built-in table extraction for this use case

### Current Limitations
- Manual column boundary detection required
- Custom logic for handling multi-page rows
- Fallback to basic table extraction when column detection fails

---

## Library Comparison

### 1. Camelot-py

**Status:** ARCHIVED (January 6, 2025) - Repository is now read-only and unmaintained

#### Installation
```bash
pip install camelot-py[cv]  # With OpenCV support
pip install camelot-py[base]  # Base installation
```

#### Best Use Cases
- PDFs with clear table borders (Lattice mode)
- Whitespace-separated tables (Stream mode)
- Documents where table positions are known
- Single or multiple tables per page

#### Pros
- **Two flavors:** Lattice (ruled lines) and Stream (whitespace)
- **High configurability:** Rich parameter set for fine-tuning
- **Pandas integration:** Direct DataFrame output
- **Multiple export formats:** CSV, JSON, Excel, HTML, Markdown, SQLite
- **Page range support:** `pages='1,4-10,20-end'` or `pages='all'`
- **Better than Tabula** for lattice cases (ruled tables)

#### Cons
- **ARCHIVED/UNMAINTAINED** as of January 2025
- **Multi-page spanning tables:** Known issue #278 - cannot handle rows spanning multiple pages
- **Requires exact boundaries:** Manual `table_areas` specification often needed
- **Dependency on OpenCV:** Can be challenging to install on some systems
- **Text-based only:** Does not work with scanned PDFs

#### Code Examples

**Basic Lattice Extraction (ruled tables):**
```python
import camelot

# Extract from specific pages
tables = camelot.read_pdf('frt.pdf', pages='1-10', flavor='lattice')

# Process each table
for table in tables:
    df = table.df  # Get pandas DataFrame
    print(f"Accuracy: {table.accuracy}")
    table.to_csv('output.csv')
```

**Stream Extraction (whitespace-separated):**
```python
# For tables without ruling lines
tables = camelot.read_pdf('frt.pdf',
                         pages='all',
                         flavor='stream',
                         row_tol=10)  # Row tolerance for grouping

# Access data
for i, table in enumerate(tables):
    print(f"Table {i}: {table.shape}")
    df = table.df
```

**Advanced Configuration with Table Areas:**
```python
# When you know exact table positions
tables = camelot.read_pdf('frt.pdf',
                         pages='10',
                         flavor='stream',
                         table_areas=['10,450,550,50', '10,750,550,450'])

# With background line processing
tables = camelot.read_pdf('frt.pdf',
                         pages='1-5',
                         flavor='lattice',
                         process_background=True,
                         line_scale=40)
```

**Multi-page Processing:**
```python
# Process all pages
tables = camelot.read_pdf('frt.pdf', pages='all', flavor='lattice')

# Process specific page range
tables = camelot.read_pdf('frt.pdf', pages='1,4-10,20-30')

# Export all tables
for i, table in enumerate(tables):
    table.to_csv(f'table_{i}.csv')
    table.to_json(f'table_{i}.json')
```

#### FRT-Specific Recommendation
**NOT RECOMMENDED** - While Camelot offers good table detection, the fact that it's now archived/unmaintained and has known issues with multi-page spanning tables makes it unsuitable for long-term use on the FRT project.

---

### 2. Tabula-py

**Status:** Actively maintained
**GitHub:** https://github.com/chezou/tabula-py

#### Installation
```bash
pip install tabula-py

# Requires Java Runtime Environment (JRE)
# Check: java -version
```

#### Best Use Cases
- Large multi-page PDF documents
- Documents with mixed table structures
- Stream extraction (whitespace-separated)
- Batch processing workflows

#### Pros
- **Battle-tested:** Wrapper around mature Tabula-Java library
- **Two modes:** Lattice (ruled) and Stream (whitespace)
- **Multi-page support:** Process all pages or specific ranges
- **Area selection:** Define exact regions with coordinates or percentages
- **Pandas integration:** Direct DataFrame output
- **Multiple outputs:** CSV, TSV, JSON
- **Better than Camelot** for stream cases (whitespace)
- **Actively maintained**

#### Cons
- **Java dependency:** Requires JRE installed
- **Stream mode limitations:** Complex table structures can be challenging
- **Manual area selection:** Often needed for accurate extraction
- **No native multi-page row handling:** Rows spanning pages require custom logic
- **Text-based only:** No OCR support

#### Code Examples

**Basic Lattice Mode:**
```python
import tabula

# Single page with lattice mode
df = tabula.read_pdf('frt.pdf',
                    pages=2,
                    lattice=True,
                    area=(406, 24, 695, 589))
```

**Stream Mode with Multiple Pages:**
```python
# Extract from all pages using stream
dfs = tabula.read_pdf('frt.pdf',
                     pages='all',
                     stream=True,
                     multiple_tables=True)

# Process each table
for i, df in enumerate(dfs):
    print(f"Table {i} shape: {df.shape}")
    df.to_csv(f'table_{i}.csv', index=False)
```

**Relative Area Selection:**
```python
# Using percentage-based area (more portable)
df = tabula.read_pdf('frt.pdf',
                    pages=2,
                    lattice=True,
                    area=(50, 5, 92, 100),  # top, left, bottom, right (%)
                    relative_area=True)
```

**Advanced Multi-page with Different Areas:**
```python
# Process multiple pages with different area selections
areas = [
    [100, 50, 600, 550],  # Page 1 area
    [120, 50, 620, 550],  # Page 2 area
    [100, 50, 600, 550],  # Page 3 area
]

all_tables = []
for page_num, area in enumerate(areas, start=1):
    df = tabula.read_pdf('frt.pdf',
                        pages=page_num,
                        stream=True,
                        area=area,
                        pandas_options={'header': None})
    all_tables.append(df)

# Concatenate all tables
import pandas as pd
combined_df = pd.concat(all_tables, ignore_index=True)
```

**Batch Conversion to CSV:**
```python
from tabula import convert_into

# Convert all pages to CSV
tabula.convert_into('frt.pdf',
                   'output.csv',
                   output_format='csv',
                   pages='all',
                   stream=True)
```

#### FRT-Specific Recommendation
**POTENTIALLY SUITABLE** - Tabula-py is mature and actively maintained. The Java dependency is a drawback, but it handles multi-page documents well. Would require custom logic for rows spanning pages, similar to current implementation.

---

### 3. PyMuPDF (fitz)

**Status:** Actively maintained (v1.23.0+)
**GitHub:** https://github.com/pymupdf/PyMuPDF

#### Installation
```bash
pip install pymupdf
```

#### Best Use Cases
- Modern PDFs with or without gridlines
- High-performance extraction needs
- OCR-based PDFs (with Tesseract integration)
- Complex table layouts
- HITL (Human In The Loop) applications

#### Pros
- **Recent table support:** Added in v1.23.0 (2023)
- **Fast performance:** C-based implementation
- **Flexible strategies:** Text, lines, or explicit detection
- **OCR integration:** Works with scanned PDFs via Tesseract
- **Pandas export:** `table.to_pandas()` method
- **Multiple formats:** Markdown, pandas, raw cells
- **Strategy parameters:** Fine-tuned control for different table types
- **No external dependencies:** (except Tesseract for OCR)

#### Cons
- **Relatively new feature:** Table extraction is newer than competitors
- **Learning curve:** Strategy parameters require experimentation
- **HITL often needed:** Complex tables may need human guidance
- **No guaranteed success:** Some table structures still challenging

#### Code Examples

**Basic Table Extraction:**
```python
import fitz

# Open PDF and extract tables
doc = fitz.open('frt.pdf')
for page_num, page in enumerate(doc):
    tabs = page.find_tables()

    if tabs.tables:
        for i, table in enumerate(tabs.tables):
            # Extract as list of lists
            data = table.extract()
            print(f"Page {page_num}, Table {i}: {len(data)} rows")
```

**Text Strategy (for tables without gridlines):**
```python
import fitz

doc = fitz.open('frt.pdf')
for page in doc:
    # Use text detection strategy for tables without visible borders
    tabs = page.find_tables(
        horizontal_strategy="text",
        vertical_strategy="text",
        text_tolerance=3,
        intersection_tolerance=5
    )

    for table in tabs:
        # Convert to pandas DataFrame
        df = table.to_pandas()
        print(df.head())
```

**Advanced Strategy Configuration:**
```python
import fitz

doc = fitz.open('frt.pdf')

for page_num in range(len(doc)):
    page = doc[page_num]

    # Fine-tuned parameters for complex tables
    tabs = page.find_tables(
        strategy="text",           # Use text boundaries
        text_tolerance=1,          # Text grouping tolerance
        intersection_tolerance=50, # Cell detection tolerance
        min_words_vertical=3,      # Minimum words for column detection
        min_words_horizontal=1     # Minimum words for row detection
    )

    for i, table in enumerate(tabs):
        # Export to different formats
        md_text = table.to_markdown()
        df = table.to_pandas()

        # Save
        df.to_csv(f'page_{page_num}_table_{i}.csv', index=False)

doc.close()
```

**Clip Region for Specific Table:**
```python
import fitz

doc = fitz.open('frt.pdf')
page = doc[0]

# Define clip region (x0, y0, x1, y1)
clip_rect = fitz.Rect(50, 100, 550, 700)

# Find tables only in clipped region
tabs = page.find_tables(
    clip=clip_rect,
    strategy="text"
)

for table in tabs:
    print("Rows:", len(table.rows))
    print("Columns:", len(table.cols))
    print(table.to_pandas())
```

**OCR-Enabled Extraction (scanned PDFs):**
```python
import fitz

# Note: Requires Tesseract OCR installed
doc = fitz.open('scanned_frt.pdf')

for page in doc:
    # PyMuPDF can invoke Tesseract automatically
    tabs = page.find_tables(
        strategy="text",
        add_lines=True  # Help with table detection
    )

    for table in tabs:
        df = table.to_pandas()
        df.to_csv('ocr_table.csv')
```

#### FRT-Specific Recommendation
**WORTH EXPLORING** - PyMuPDF's text strategy mode could work well for FRT tables. The strategy parameters offer fine-tuned control similar to current custom implementation. Performance would likely be better than current approach.

---

### 4. pdfplumber (Enhanced Table Methods)

**Status:** Actively maintained
**Current in use:** Yes (custom column extraction)

#### Installation
```bash
pip install pdfplumber
```

#### Best Use Cases
- Complex table structures
- Custom table detection logic
- Multi-line cells
- Fine-grained control over extraction

#### Pros
- **Already in use:** Team familiarity
- **Detailed layout analysis:** Access to chars, words, rects, lines
- **Custom table settings:** Extensive configuration options
- **Built on pdfminer.six:** Robust text extraction
- **Active community:** Good documentation and examples
- **Explicit line control:** Define table boundaries manually

#### Cons
- **Complex API:** Requires understanding of many parameters
- **Multi-page tables:** No native support for spanning tables
- **Trial and error:** Often needs experimentation with settings
- **Performance:** Slower than PyMuPDF for large documents

#### Code Examples

**Standard Table Extraction:**
```python
import pdfplumber

with pdfplumber.open('frt.pdf') as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()

        for table in tables:
            # Convert to DataFrame
            import pandas as pd
            df = pd.DataFrame(table[1:], columns=table[0])
            print(df.head())
```

**Custom Table Settings:**
```python
import pdfplumber

# Define custom table settings
table_settings = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "explicit_vertical_lines": [],  # Add if needed
    "explicit_horizontal_lines": [],  # Add if needed
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "edge_min_length": 3,
    "min_words_vertical": 3,
    "min_words_horizontal": 1,
    "text_tolerance": 3,
    "text_keep_blank_chars": True  # Important for complex tables
}

with pdfplumber.open('frt.pdf') as pdf:
    for page in pdf.pages:
        tables = page.extract_tables(table_settings=table_settings)
```

**Explicit Lines for Better Control:**
```python
import pdfplumber

with pdfplumber.open('frt.pdf') as pdf:
    page = pdf.pages[0]

    # Define explicit vertical lines (x-coordinates)
    v_lines = [50, 150, 250, 350, 450, 550]

    # Define explicit horizontal lines (y-coordinates)
    h_lines = [100, 120, 140, 160, 180, 200]

    table_settings = {
        "explicit_vertical_lines": v_lines,
        "explicit_horizontal_lines": h_lines,
        "intersection_tolerance": 5
    }

    tables = page.extract_tables(table_settings=table_settings)
```

**Multi-page Table Reconstruction:**
```python
import pdfplumber

# Extract table structure from first page for consistency
with pdfplumber.open('frt.pdf') as pdf:
    first_page = pdf.pages[0]

    # Get vertical line positions from first page
    v_lines = [line['x0'] for line in first_page.lines if line['height'] > 50]

    all_rows = []

    for page in pdf.pages:
        table_settings = {
            "explicit_vertical_lines": v_lines,
            "text_keep_blank_chars": True,
            "intersection_tolerance": 3
        }

        tables = page.extract_tables(table_settings=table_settings)

        for table in tables:
            all_rows.extend(table)

    # Combine all rows
    import pandas as pd
    df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
```

**Word-Based Extraction (Similar to Current FRT Implementation):**
```python
import pdfplumber

with pdfplumber.open('frt.pdf') as pdf:
    page = pdf.pages[0]

    # Extract words with positions
    words = page.extract_words(
        x_tolerance=3,
        y_tolerance=3,
        keep_blank_chars=False
    )

    # Detect column boundaries from header
    header_words = [w for w in words if w['top'] < 100]  # Adjust threshold
    header_words.sort(key=lambda w: w['x0'])

    # Create column boundaries
    columns = []
    for i, word in enumerate(header_words):
        x_start = word['x0']
        x_end = header_words[i+1]['x0'] if i+1 < len(header_words) else page.width
        columns.append({
            'name': word['text'],
            'x_start': x_start,
            'x_end': x_end
        })
```

#### FRT-Specific Recommendation
**CURRENT CHOICE** - Already using pdfplumber with custom column-based extraction. The built-in table extraction methods could be explored as an alternative to custom logic, but current approach seems well-suited.

---

### 5. pdfminer.six

**Status:** Actively maintained
**Note:** Foundation for pdfplumber

#### Installation
```bash
pip install pdfminer.six
```

#### Best Use Cases
- Low-level PDF text extraction
- Custom parsing logic
- Understanding PDF structure
- Building custom extraction tools

#### Pros
- **Low-level access:** Complete control over PDF structure
- **Layout analysis:** Detailed positioning information
- **Foundation library:** Powers pdfplumber
- **Multiple output formats:** Text, HTML, hOCR
- **Active maintenance:** Released November 2025

#### Cons
- **No table extraction:** Must build custom logic
- **Complex API:** Steep learning curve
- **Low-level only:** Need significant custom code
- **Better alternatives exist:** pdfplumber is built on this

#### Code Example
```python
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer

# Simple text extraction
text = extract_text('frt.pdf')

# Detailed layout extraction
for page_layout in extract_pages('frt.pdf'):
    for element in page_layout:
        if isinstance(element, LTTextContainer):
            print(f"Position: {element.bbox}")
            print(f"Text: {element.get_text()}")
```

#### FRT-Specific Recommendation
**NOT RECOMMENDED** - No table extraction capabilities. Use pdfplumber instead (which is built on pdfminer.six).

---

### 6. pypdf

**Status:** Actively maintained (successor to PyPDF2)
**Note:** PyPDF2 is deprecated

#### Installation
```bash
pip install pypdf
```

#### Best Use Cases
- PDF merging and splitting
- PDF metadata manipulation
- Page rotation and cropping
- PDF encryption/decryption

#### Pros
- **PDF manipulation:** Excellent for merging, splitting, rotating
- **Metadata handling:** Read/write PDF properties
- **Encryption support:** Password-protected PDFs
- **Modern replacement:** Successor to PyPDF2

#### Cons
- **No table extraction:** Not designed for this purpose
- **Text extraction only:** Basic text retrieval
- **Better alternatives exist:** For table extraction

#### FRT-Specific Recommendation
**NOT RECOMMENDED** - No table extraction capabilities. Use specialized table extraction libraries.

---

### 7. Deep Learning Models

#### Table Transformer (Microsoft)

**Status:** Research project, actively maintained
**GitHub:** https://github.com/microsoft/table-transformer

##### Installation
```bash
pip install table-transformer
# Or clone and install from repo
git clone https://github.com/microsoft/table-transformer
cd table-transformer
pip install -e .
```

##### Best Use Cases
- Scanned documents
- Complex table layouts
- Research and academic documents
- When traditional methods fail

##### Pros
- **State-of-the-art accuracy:** Deep learning-based
- **Handles complex structures:** Nested tables, merged cells
- **Scanned PDFs:** Works with images
- **Multiple output formats:** HTML, CSV, bounding boxes
- **Pre-trained models:** PubTables-1M, FinTabNet.c
- **GriTS metric:** Evaluation benchmark included

##### Cons
- **Requires OCR:** Separate text extraction needed (Tesseract)
- **Computational overhead:** GPU recommended
- **Setup complexity:** More dependencies
- **Slower processing:** Compared to rule-based methods
- **Research focus:** May lack production polish

##### Code Example
```python
from table_transformer import TableTransformerForObjectDetection
from transformers import AutoImageProcessor
from PIL import Image
import torch

# Load pre-trained model
model = TableTransformerForObjectDetection.from_pretrained(
    "microsoft/table-transformer-detection"
)
processor = AutoImageProcessor.from_pretrained(
    "microsoft/table-transformer-detection"
)

# Process PDF page as image
image = Image.open('page.png')  # Convert PDF page to image first
inputs = processor(images=image, return_tensors="pt")

# Detect tables
with torch.no_grad():
    outputs = model(**inputs)

# Process results
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(
    outputs, threshold=0.9, target_sizes=target_sizes
)[0]

# Extract detected tables
for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    box = [round(i, 2) for i in box.tolist()]
    print(f"Detected table with confidence {round(score.item(), 3)} at {box}")
```

##### FRT-Specific Recommendation
**OVERKILL** - The FRT PDFs are text-based, not scanned. Deep learning models add unnecessary complexity and computational overhead for this use case. Traditional methods are more appropriate.

---

#### LayoutLMv3 (Microsoft)

**Status:** Research model
**Hugging Face:** microsoft/layoutlmv3

##### Installation
```bash
pip install transformers
pip install layoutparser
```

##### Best Use Cases
- Document understanding tasks
- Classification and information extraction
- Combined text and layout analysis
- Research applications

##### Pros
- **Multi-modal:** Understands text and layout
- **Pre-trained:** Available on Hugging Face
- **Versatile:** Document classification, QA, extraction
- **State-of-the-art:** Recent research advances

##### Cons
- **Not table-specific:** General document understanding
- **Requires fine-tuning:** For specific tasks
- **Computational intensive:** GPU needed
- **Complex setup:** Significant learning curve
- **Better tools exist:** For pure table extraction

##### Code Example
```python
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from PIL import Image
import torch

# Load model
processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
model = LayoutLMv3ForTokenClassification.from_pretrained("microsoft/layoutlmv3-base")

# Process document
image = Image.open('page.png')
encoding = processor(image, return_tensors="pt")

# Get predictions
with torch.no_grad():
    outputs = model(**encoding)
    predictions = outputs.logits.argmax(-1)
```

##### FRT-Specific Recommendation
**NOT RECOMMENDED** - Designed for document understanding, not specifically table extraction. Too complex for the FRT use case.

---

## Multi-Page Spanning Table Capabilities Summary

| Library | Native Multi-page Support | Row Spanning | Custom Logic Needed |
|---------|---------------------------|--------------|---------------------|
| **Camelot-py** | No (known issue #278) | No | Yes (complex) |
| **Tabula-py** | Pages parameter | No | Yes (moderate) |
| **PyMuPDF** | Page iteration | No | Yes (moderate) |
| **pdfplumber** | Page iteration | No | Yes (current approach) |
| **pdfminer.six** | Page iteration | No | Yes (extensive) |
| **pypdf** | N/A (no table support) | N/A | N/A |
| **Table Transformer** | Via preprocessing | Potentially | Yes (with OCR) |
| **LayoutLMv3** | Via preprocessing | Potentially | Yes (with fine-tuning) |

---

## Recommendations for FRT Parser

### Option 1: Continue with Enhanced pdfplumber (RECOMMENDED)
**Approach:** Keep current column-based approach, explore pdfplumber's table extraction

**Pros:**
- Team already familiar with pdfplumber
- Current implementation works well
- Can experiment with built-in table methods as alternative
- No new dependencies

**Implementation:**
```python
# Try pdfplumber's table extraction with custom settings
table_settings = {
    "explicit_vertical_lines": detected_columns,
    "text_keep_blank_chars": True,
    "intersection_tolerance": 3,
    "vertical_strategy": "explicit",
    "horizontal_strategy": "text"
}

tables = page.extract_tables(table_settings=table_settings)
```

### Option 2: Migrate to PyMuPDF (WORTH EXPLORING)
**Approach:** Test PyMuPDF's text strategy for table detection

**Pros:**
- Better performance than pdfplumber
- Text strategy well-suited for FRT structure
- No Java dependency
- Modern, actively maintained

**Implementation:**
```python
import fitz

doc = fitz.open('frt.pdf')
all_records = []

for page in doc:
    tabs = page.find_tables(
        horizontal_strategy="text",
        vertical_strategy="text",
        text_tolerance=3
    )

    for table in tabs:
        df = table.to_pandas()
        all_records.extend(df.to_dict('records'))
```

### Option 3: Hybrid Approach (EXPERIMENTAL)
**Approach:** Use Tabula-py for initial extraction, custom logic for row spanning

**Pros:**
- Tabula good for multi-page processing
- Battle-tested on large documents
- Could reduce custom logic

**Cons:**
- Java dependency
- Still requires custom row-spanning logic

### Option 4: Deep Learning (NOT RECOMMENDED)
**Reason:** Unnecessary complexity for text-based PDFs

---

## Implementation Priority

1. **Phase 1: Benchmark Current System**
   - Document current performance (time, accuracy)
   - Identify specific pain points
   - Create test dataset with known edge cases

2. **Phase 2: Test PyMuPDF**
   - Implement proof-of-concept with PyMuPDF
   - Compare performance and accuracy
   - Evaluate ease of maintenance

3. **Phase 3: Explore pdfplumber Table Methods**
   - Test built-in table extraction with custom settings
   - Compare with current column-based approach
   - Assess if it simplifies code

4. **Phase 4: Decision**
   - Stick with current approach (if working well)
   - Migrate to PyMuPDF (if significantly better)
   - Hybrid approach (if benefits outweigh complexity)

---

## Key Findings

1. **Camelot-py is archived** - No longer maintained as of January 2025
2. **No library natively handles row spanning** - All require custom logic
3. **PyMuPDF shows promise** - Text strategy could work well for FRT
4. **Current approach is reasonable** - pdfplumber with custom logic is valid
5. **Deep learning is overkill** - Not needed for text-based PDFs
6. **Java dependency is a drawback** - Tabula-py requires JRE

---

## Additional Resources

### Documentation Links
- **Camelot:** https://camelot-py.readthedocs.io/
- **Tabula-py:** https://tabula-py.readthedocs.io/
- **PyMuPDF:** https://pymupdf.readthedocs.io/
- **pdfplumber:** https://github.com/jsvine/pdfplumber
- **Table Transformer:** https://github.com/microsoft/table-transformer
- **LayoutLMv3:** https://huggingface.co/microsoft/layoutlmv3

### Comparative Studies
- "Python Libraries to Extract Tables From PDF: A Comparison" - https://unstract.com/blog/extract-tables-from-pdf-python/
- "Comparing 6 Frameworks for Rule-based PDF parsing" - https://www.ai-bites.net/comparing-6-frameworks-for-rule-based-pdf-parsing/
- "A Comparative Study of PDF Parsing Tools" - https://arxiv.org/html/2410.09871v1

---

## Conclusion

The current pdfplumber implementation with custom column-based extraction is a solid approach. Before making major changes:

1. Benchmark current performance
2. Test PyMuPDF as primary alternative
3. Consider if complexity of migration justifies benefits
4. Keep solution maintainable and well-documented

**Best path forward:** Create proof-of-concept with PyMuPDF to compare against current implementation. If performance gains are significant and code complexity is similar or reduced, consider migration. Otherwise, stick with current approach.
