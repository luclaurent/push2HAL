# Configuration

## Credentials

HAL credentials are required for all upload operations. Store them in a JSON file, typically `~/.apihal`:

```json
{
  "login": "your-hal-username",
  "passwd": "your-hal-password"
}
```

**Permissions:** Credentials file should be readable only by you:

```bash
chmod 600 ~/.apihal
```

### Alternative: Command-Line Arguments

Pass credentials inline instead of file:

```bash
json2hal metadata.json -l username -p password
```

### Alternative: Environment Variables

Set `HAL_LOGIN` and `HAL_PASSWD`:

```bash
export HAL_LOGIN=username
export HAL_PASSWD=password
json2hal metadata.json
```

**Priority Order:**
1. Command-line arguments (`-l`, `-p`)
2. Environment variables (`HAL_LOGIN`, `HAL_PASSWD`)
3. Credentials file (`.apihal` in home or project directory)

---

## JSON Metadata Schema

Document metadata is specified in JSON format. Here are the most common fields:

### Basic Fields

```json
{
  "type": "article",
  "title": {
    "en": "English Title",
    "fr": "French Title"
  },
  "abstract": {
    "en": "English abstract...",
    "fr": "French abstract..."
  },
  "keywords": {
    "en": ["keyword1", "keyword2"],
    "fr": ["mot-clé1", "mot-clé2"]
  }
}
```

- **type** (string, required): Document type code
  - Supported types: `article`, `book`, `bookcapter`, `thesis`, `conference`, `poster`, `report`, etc.
  - See [API Reference](api.md) for complete list

- **title** (object, required): Document title in one or more languages
  - Keys: `en`, `fr`, `es`, `de`, etc. (ISO 639-1 language codes)
  - Use English if French not available

- **abstract** (object): Document abstract
  - Same structure as `title`

- **keywords** (object): Keywords/subject terms
  - Value is array of strings
  - Should be specific to document scope

### Authors & Contributors

```json
{
  "authors": [
    {
      "firstname": "John",
      "lastname": "Doe",
      "affiliation": "University of Example"
    },
    {
      "firstname": "Jane",
      "lastname": "Smith",
      "affiliation": "Example Institute",
      "email": "jane@example.edu"
    }
  ]
}
```

- **authors** (array): Document authors
  - Required fields: `firstname`, `lastname`
  - Optional: `affiliation`, `email`, `halAuthorId` (if author already in HAL)

- **contributors** (array): Additional contributors (editors, translators, etc.)
  - Same structure as `authors`
  - Use for books with editors, translated works, etc.

### Publication Details

```json
{
  "journal": "IEEE Transactions on Software Engineering",
  "volume": "48",
  "issue": "2",
  "pages": "123-145",
  "issn": "0098-5589",
  "year": 2022,
  "month": 2,
  "day": 15
}
```

- **journal** (string): Journal name
  - Used for articles; required for journal papers

- **volume**, **issue**, **pages** (string): Volume, issue, page numbers
  - Format: "123-145" for page range

- **issn** (string): Journal ISSN
  - Format: "1234-5678"

- **year**, **month**, **day** (integer): Publication date
  - `year` required; `month` and `day` optional

### Online Information

```json
{
  "url": "https://doi.org/10.1234/example",
  "doi": "10.1234/example",
  "publisherLink": "https://example.com/paper",
  "file": "article.pdf"
}
```

- **url** (string): Primary document URL (often DOI)

- **doi** (string): Digital Object Identifier
  - Format: "10.xxxx/xxxx" (include prefix)

- **publisherLink** (string): Link to publisher's version

- **file** (string): Path to PDF file for upload
  - Relative to current directory or absolute path
  - Optional; can be provided separately with `pdf2hal`

### Subject Classification

```json
{
  "domaines": ["info", "math"],
  "disciplines": ["computer-science", "mathematics"]
}
```

- **domaines** (array): HAL domain codes
  - Examples: `info` (computer science), `math` (mathematics), `phys` (physics), `shs` (humanities)

- **disciplines** (array): More specific discipline codes
  - Refines the domain classification

### Update-Specific Options

```json
{
  "updateType": "file",
  "fileUpload": "new_version.pdf"
}
```

- **updateType** (string): Type of update
  - `file`: Replace PDF only
  - `metadata`: Update metadata only
  - `all`: Update both (default)

---

## Complete JSON Example

```json
{
  "type": "article",
  "title": {
    "en": "Machine Learning for Academic Document Classification",
    "fr": "Apprentissage automatique pour la classification de documents académiques"
  },
  "abstract": {
    "en": "This paper presents a novel approach to automatic classification of academic documents using deep learning...",
    "fr": "Cet article présente une nouvelle approche de classification automatique de documents académiques utilisant l'apprentissage profond..."
  },
  "keywords": {
    "en": ["machine learning", "document classification", "neural networks"],
    "fr": ["apprentissage automatique", "classification de documents", "réseaux de neurones"]
  },
  "authors": [
    {
      "firstname": "Alice",
      "lastname": "Johnson",
      "affiliation": "Stanford University"
    },
    {
      "firstname": "Bob",
      "lastname": "Chen",
      "affiliation": "MIT",
      "email": "bchen@mit.edu"
    }
  ],
  "journal": "IEEE Transactions on Machine Learning",
  "volume": "45",
  "issue": "3",
  "pages": "234-256",
  "issn": "2162-2388",
  "year": 2023,
  "month": 3,
  "day": 15,
  "doi": "10.1234/ml.2023.001",
  "url": "https://doi.org/10.1234/ml.2023.001",
  "domaines": ["info"],
  "disciplines": ["computer-science", "machine-learning"],
  "file": "paper.pdf"
}
```

---

## Server Modes

### Preprod (Default)

- **URL:** https://preprod.hal.science
- **Purpose:** Testing and validation
- **Data:** Separate from production; cleared periodically
- **Use:** Always test new workflows here first

### Production

- **URL:** https://hal.science
- **Purpose:** Official HAL repository
- **Data:** Permanent; publicly searchable
- **Use:** Only after validating in preprod

### Test (Development Only)

- **URL:** https://test.hal.science
- **Purpose:** Internal HAL testing
- **Data:** Ephemeral; not backed up
- **Use:** Only for development/debugging

**Selection:**

```bash
json2hal metadata.json -c ~/.apihal            # Uses preprod (default)
json2hal metadata.json -c ~/.apihal --prod     # Uses production
json2hal metadata.json -c ~/.apihal --test     # Uses test server
```

---

## Default Settings

push2HAL uses sensible defaults for most operations. Defaults are defined in `src/push2HAL/default.py`:

| Setting | Default | Override |
|---------|---------|----------|
| Server | preprod | `--prod`, `--test` |
| Upload directory | `.` (current directory) | `--dirpath` |
| XML filename | `upload.xml` | `--xmlfile` |
| Config file | `~/.apihal` | `-c` / `--credentials` |
| Verbose logging | Off | `--verbose` |
| SWORD mode | Test mode | `--prod` for production |

---

## Environment Setup

### Installation

```bash
# From PyPI
pip install push2HAL

# From source
cd /path/to/push2HAL
pip install .

# With development dependencies
pip install -e ".[dev]"
```

### Python Version

- **Minimum:** Python 3.8
- **Recommended:** Python 3.10+
- **Current CI:** Python 3.13

### Dependencies

Core dependencies (installed automatically):

- `lxml` — XML parsing and building
- `loguru` — Structured logging
- `requests` — HTTP communication with HAL
- `pdfplumber` — PDF text extraction
- `unidecode` — Character normalization
- `stdnum` — ISBN/ISSN validation

Optional dependencies:

- `pytest` — Testing (dev only)
- `sphinx` — Documentation generation (dev only)

Check `pyproject.toml` for complete dependency list.

---

## Troubleshooting

### Module Not Found

```
ModuleNotFoundError: No module named 'push2HAL'
```

**Solution:** Ensure package is installed (`pip install .`) and you're in the correct environment.

### Credentials Not Found

```
Error: Configuration error (78): No credentials found
```

**Solutions:**
1. Create `~/.apihal` with credentials
2. Or pass `-l username -p password`
3. Or set `HAL_LOGIN` and `HAL_PASSWD` environment variables

### Invalid Metadata

```
Error: Software error (70): Invalid metadata
```

**Solutions:**
1. Validate JSON against schema in this document
2. Check for typos in field names
3. Ensure required fields are present
4. Verify data types (e.g., year should be integer, not string)

### Server Unreachable

```
Error: Connection failed
```

**Solutions:**
1. Check internet connection
2. Verify HAL server is online
3. Try different server mode (preprod vs prod)
4. Add `--verbose` to see detailed error

---

## References

- [HAL Documentation](https://doc.archives-ouvertes.fr)
- [HAL API Reference](https://api.archives-ouvertes.fr/docs/search)
- [TEI Schema](https://hal.archives-ouvertes.fr/documents/aofr.xsd)
- [SWORD Protocol](http://www.swordapp.org/)
