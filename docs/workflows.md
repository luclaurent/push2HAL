# Workflows

## Common Usage Patterns

### Create a New HAL Entry from JSON

**Scenario:** You have a journal article published in an online repository and want to deposit it in HAL with metadata.

**Files:**
- `article.json` — Metadata (title, authors, abstract, etc.)
- `article.pdf` — Article PDF (optional)

**Command:**

```bash
json2hal article.json -c ~/.apihal
```

**Python API:**

```python
from push2HAL.execHAL import runJSON2HAL

status = runJSON2HAL(
    jsonContent='article.json',
    credentials={'login': 'user', 'passwd': 'pass'},
    prod='preprod'
)
print(f"Status: {status}")
```

**What happens:**
1. JSON is parsed; `type` field determines document class
2. TEI XML is built from metadata
3. File is written to `upload.xml` in current directory
4. SWORD client uploads file to HAL preprod
5. HAL returns a HAL ID (e.g., `hal-01234567`)

**Output:** Check preprod.hal.science with your HAL ID for the new entry

---

### Update an Existing HAL Entry

**Scenario:** Your article is already in HAL but needs metadata corrections or a new abstract.

**Files:**
- `update.json` — Metadata updates (only include fields to change)

**Command:**

```bash
push2hal update -c ~/.apihal --halid hal-01234567 --json update.json
```

**Python API:**

```python
from push2HAL.execHAL import updateHAL

status = updateHAL(
    data='update.json',
    halid='hal-01234567',
    credentials={'login': 'user', 'passwd': 'pass'},
    prod='preprod'
)
```

**What happens:**
1. Existing HAL entry is retrieved from HAL API
2. Update JSON is merged (new fields override existing)
3. Document type is preserved from HAL (not changed by update)
4. TEI XML is regenerated with updates
5. File is uploaded back to HAL (SWORD PUT)

**Important:** The document type is inferred from the existing HAL entry and preserved. If you want to change types, contact HAL administrators.

---

### Add a PDF to an Existing Entry

**Scenario:** Your entry exists in HAL but is missing the PDF. You want to upload the full text.

**Files:**
- `article.pdf` — Article PDF

**Command:**

```bash
pdf2hal article.pdf -a hal-01234567 -c ~/.apihal
```

**Python API:**

```python
from push2HAL.execHAL import runPDF2HAL

status = runPDF2HAL(
    pdf_path='article.pdf',
    halid='hal-01234567',
    credentials={'login': 'user', 'passwd': 'pass'},
    prod='preprod'
)
```

**What happens:**
1. PDF is analyzed to extract title (for validation)
2. Existing HAL entry is retrieved
3. TEI XML is loaded (to preserve all metadata)
4. PDF is added to the upload payload
5. Files are packaged as ZIP (XML + PDF)
6. ZIP is uploaded to HAL

**Result:** PDF is now attached to the HAL entry; readers can download it

---

### Batch Create Multiple Entries

**Scenario:** You have 100 articles to deposit. Each has a JSON metadata file.

**Script Example:**

```python
from push2HAL.execHAL import runJSON2HAL
import os
from pathlib import Path

credentials = {'login': 'user', 'passwd': 'pass'}
json_dir = 'articles/'

for json_file in sorted(Path(json_dir).glob('*.json')):
    print(f"Processing {json_file}...")
    status = runJSON2HAL(
        jsonContent=str(json_file),
        credentials=credentials,
        prod='preprod',
        verbose=True
    )
    if status == 0:
        print(f"  ✓ Success")
    else:
        print(f"  ✗ Failed with status {status}")
```

---

### Search & Update Workflow

**Scenario:** You want to find HAL entries matching certain criteria and update all of them.

**Script Example:**

```python
from push2HAL.libAPIHAL import APIHAL
from push2HAL.execHAL import updateHAL
import json

# Search HAL
api = APIHAL()
results = api.search('affFiltered_s:"Cnam" AND year_int:[2023 TO 2024]')

credentials = {'login': 'user', 'passwd': 'pass'}

for result in results:
    halid = result.get('halId_s', [None])[0]
    print(f"Updating {halid}...")
    
    # Update with new data
    update_data = {
        'keywords': {'en': ['machine learning', 'AI']}
    }
    
    status = updateHAL(
        data=update_data,
        halid=halid,
        credentials=credentials,
        prod='preprod'
    )
```

---

## CLI Reference

### json2hal

Create new HAL entries from JSON metadata.

```bash
json2hal <json_file> [options]
```

**Arguments:**
- `json_file` — Path to JSON metadata file

**Options:**
- `-c, --credentials FILE` — Credentials file (default: `~/.apihal`)
- `-l, --login USER` — HAL username (if not in credentials file)
- `-p, --passwd PASS` — HAL password (if not in credentials file)
- `--prod` — Use production server (default: preprod)
- `--test` — Use test server
- `--verbose` — Enable debug logging
- `--grobid [grobid_options]` — Enable Grobid service for fulltext extraction
- `--completion [options]` — PDF text completion options
- `--idhal USER` — Deposit on behalf of another user (requires permissions)
- `-h, --help` — Show help

**Environment Variables:**
- `HAL_LOGIN` — HAL username
- `HAL_PASSWD` — HAL password

**Examples:**

```bash
# Create with credentials file
json2hal metadata.json -c ~/.apihal

# Create on production with inline credentials
json2hal metadata.json -l myuser -p mypass --prod

# Create with verbose logging
json2hal metadata.json -c ~/.apihal --verbose
```

---

### pdf2hal

Add PDF files to existing HAL entries.

```bash
pdf2hal <pdf_file> [options]
```

**Arguments:**
- `pdf_file` — Path to PDF file

**Options:**
- `-a, --halid HAL_ID` — Target HAL ID (required if no interactive search)
- `-c, --credentials FILE` — Credentials file (default: `~/.apihal`)
- `-l, --login USER` — HAL username
- `-p, --passwd PASS` — HAL password
- `--prod` — Use production server (default: preprod)
- `--no-interact` — Disable interactive mode (fail if no HAL ID provided)
- `--verbose` — Enable debug logging
- `-h, --help` — Show help

**Interactive Mode:**

If no `--halid` is provided, pdf2hal will:
1. Extract title from PDF
2. Search HAL for matching entries
3. Display results (numbered list)
4. Prompt you to choose one

**Examples:**

```bash
# Add PDF with known HAL ID
pdf2hal article.pdf -a hal-01234567 -c ~/.apihal

# Interactive search (will prompt for selection)
pdf2hal article.pdf -c ~/.apihal

# Disable interaction (useful in scripts)
pdf2hal article.pdf -a hal-01234567 -c ~/.apihal --no-interact
```

---

### push2hal

Multi-command tool for create, update, and PDF operations.

```bash
push2hal <command> [options]
```

**Commands:**

#### create
Create a new HAL entry.

```bash
push2hal create -j metadata.json -c ~/.apihal [--prod]
```

Options: Same as `json2hal`

#### update
Update an existing HAL entry.

```bash
push2hal update --halid hal-01234567 -j update.json -c ~/.apihal [--prod]
```

**Additional Options:**
- `-j, --json FILE` — JSON with updates
- `--halid ID` — Target HAL ID (required)

#### pdf
Add PDF to HAL entry.

```bash
push2hal pdf <pdf_file> -a hal-01234567 -c ~/.apihal [--prod]
```

Options: Same as `pdf2hal`

#### search
Search HAL and display results.

```bash
push2hal search '<query>' [-c credentials] [--prod]
```

**Options:**
- `-c, --credentials FILE` — Credentials file (for authentication)
- `--prod` — Use production server
- `--format [json|xml|bibtex]` — Output format (default: text summary)

**Query Syntax:** Standard Solr query syntax (see [HAL API documentation](https://api.archives-ouvertes.fr/docs/search))

#### help
Show help for a command.

```bash
push2hal help [command]
```

---

## JSON Metadata Schema

See [Configuration](configuration.md) for complete field documentation and examples.

---

## Error Handling

### Common Issues

**"Configuration error (78)"**
- **Cause:** Missing or invalid credentials
- **Solution:** Ensure credentials file exists at `~/.apihal` or pass `-l` and `-p` options

**"Software error (70)"**
- **Cause:** Invalid metadata (e.g., bad ISSN, missing required fields)
- **Solution:** Check JSON against schema in [Configuration](configuration.md); verify with `push2hal validate file.json`

**"OSFile error (72)"**
- **Cause:** File not found (JSON, PDF, or XML)
- **Solution:** Check file paths are correct and files exist

**"SWORD error 400"**
- **Cause:** Metadata validation failed (HAL-side)
- **Solution:** Check HAL's error message in terminal output; revise metadata

**"HAL ID not found"**
- **Cause:** Update or PDF upload to non-existent HAL ID
- **Solution:** Verify HAL ID is correct; check on [preprod.hal.science](https://preprod.hal.science)

---

## Tips & Best Practices

1. **Always test in preprod first:** Use `--preprod` (default) before `--prod`
2. **Batch operations:** Use Python API in a loop for multiple entries
3. **Credentials:** Never commit `.apihal` to version control; use `.gitignore`
4. **Validation:** Run `push2hal validate` before uploading if unsure
5. **Search before upload:** Check if entry already exists to avoid duplicates
6. **PDF last:** Upload metadata first, then add PDF; easier to troubleshoot
