# Development

## Getting Started

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/luclaurent/push2HAL.git
cd push2HAL

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

### Project Structure

```
push2HAL/
├── src/push2HAL/          # Main package
│   ├── elementHAL.py      # Core HALelt classes
│   ├── execHAL.py         # Workflow orchestration
│   ├── libHAL.py          # XML/SWORD operations
│   ├── libAPIHAL.py       # HAL API communication
│   ├── misc.py            # Utilities
│   ├── default.py         # Configuration constants
│   └── __init__.py        # Package entry point
├── tests/                 # Test suite
│   ├── test_elementHAL.py # Unit tests
│   └── ...
├── docs/                  # Documentation
├── examples/              # Example JSON, XML files
├── pyproject.toml         # Package metadata & dependencies
└── README.md              # Quick start guide
```

---

## Code Organization

### elementHAL.py

Core object model for HAL documents.

**Key Classes:**
- `HALelt` — Abstract base class
- `Article` — Journal articles (HAL type ART)
- `Book` — Books (type OUV)
- `Thesis` — PhD theses (type THESE)
- ...40+ document type subclasses

**Key Methods:**
- `from_type(typeDoc, data)` — Factory: instantiate by type name
- `from_input(data)` — Factory: auto-detect type from JSON
- `fromXMLContent(xmlSource, data)` — Factory: load TEI, infer type
- `loadData(data)` — Load metadata from dict or JSON file
- `loadXML(xmlSource)` — Load TEI XML
- `populate()` — Build XML from metadata
- `prepare()` — Prepare upload payload
- `upload()` — Execute upload to HAL

**Design:** Subclasses are thin wrappers around `HALelt` with `HAL_TYPE` set. Most behavior is in base class.

### execHAL.py

High-level orchestration for user-facing workflows.

**Key Functions:**
- `runJSON2HAL()` — Create new entry from JSON
- `updateHAL()` — Update existing entry
- `runPDF2HAL()` — Add PDF to entry

**Design:** Each function validates inputs, loads credentials, creates a `HALelt` instance, and calls its methods.

### libHAL.py

Low-level XML building and SWORD communication.

**Key Functions:**
- `buildXML(data, inTree)` — Build TEI XML from metadata
- `preparePayload()` — Prepare files and SWORD headers
- `upload2HAL()` — POST/PUT to HAL SWORD endpoint
- `getTypeDoc()` — Resolve type code

**Per-Field Functions:**
- `setTitles()` — Add title element
- `setAuthors()` — Add author elements
- `setAbstract()` — Add abstract
- ...dozens more for all metadata fields

**Design:** Procedural-style functions operating on `lxml.etree` elements. Reusable by other tools or scripts.

### libAPIHAL.py

Communicate with HAL's Solr-based search API.

**Key Classes:**
- `APIHAL` — Search documents
- `APIHALauthor` — Query authors
- `APIHALstructure` — Query institutions
- `APIHALjounal` — Query journals

**Key Methods:**
- `search(query)` — Execute Solr query, return results
- `directAccess(hal_id, format)` — Fetch specific document

**Design:** OOP wrappers around HTTP requests; result parsing to Python dicts.

### misc.py

General-purpose utilities.

**Key Functions:**
- `load_credentials()` — Load HAL credentials from file/args/env
- `writeXML(root, filename)` — Write `lxml.etree.Element` to file
- `checkXML(filename)` — Validate XML against XSD schema
- `extract_info(pdf_path)` — Extract metadata from PDF
- `adapt_headers_*()` — SWORD header utility functions

**Design:** Stateless functions; no side effects except file I/O and logging.

### default.py

Constants, configuration, and mappings.

**Key Definitions:**
- HAL API URLs (`API_URL_PREPROD`, `API_URL_PROD`)
- Default file names
- SWORD mode settings
- Document type mappings
- TEI namespace URLs
- XSD schema paths

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_elementHAL.py -v
```

### Run Specific Test

```bash
pytest tests/test_elementHAL.py::test_from_type_returns_specialized_class -v
```

### Coverage Report

```bash
pytest tests/ --cov=src/push2HAL --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Structure

Each test file follows the pattern:

```python
import pytest
from push2HAL import elementHAL as elt

class TestFactoryMethods:
    def test_from_type_returns_specialized_class(self):
        """Factory should instantiate correct document subclass."""
        doc = elt.HALelt.from_type('article', {})
        assert isinstance(doc, elt.Article)
    
    # ... more tests
```

**Test Naming:** `test_<function>_<behavior>` describes what is being tested and expected outcome.

### Fixtures

Use pytest fixtures for common setup:

```python
@pytest.fixture
def sample_article_json():
    """Valid article metadata."""
    return {
        'type': 'article',
        'title': {'en': 'Test Article'},
        'authors': [{'firstname': 'John', 'lastname': 'Doe'}]
    }

def test_load_data_updates_existing_xml_tree(sample_article_json):
    doc = elt.Article(sample_article_json)
    assert doc.data is not None
```

---

## Adding a New Document Type

### Step 1: Define the Subclass

Edit `src/push2HAL/elementHAL.py`:

```python
class YourDocType(HALelt):
    """Description of your document type."""
    HAL_TYPE = "YOUR_TYPE_CODE"
```

### Step 2: Register in Type Map

At the end of `elementHAL.py`, add to `_TYPE_TO_CLASS`:

```python
_TYPE_TO_CLASS = {
    # ... existing types ...
    'yourdoctype': YourDocType,
}
```

### Step 3: Test Instantiation

```python
def test_your_doc_type(self):
    doc = HALelt.from_type('yourdoctype', {})
    assert isinstance(doc, YourDocType)
    assert doc.HAL_TYPE == "YOUR_TYPE_CODE"
```

### Step 4: Add Tests (Optional)

Create focused tests if the type has special behavior.

---

## Extending with Custom Metadata Fields

### Step 1: Add Field Setter to libHAL.py

```python
def setCustomField(inTree, data):
    """Add custom field to TEI XML."""
    custom_value = data.get('custom_field')
    if custom_value:
        # Build XML elements as needed
        # e.g., elem = etree.SubElement(parent, 'element')
        # elem.text = custom_value
        pass
    return inTree
```

### Step 2: Call from buildXML

In `libHAL.buildXML()`, add:

```python
inTree = setCustomField(inTree, data)
```

### Step 3: Document in Configuration

Add to `docs/configuration.md` with field description and example.

### Step 4: Test

```python
def test_custom_field_added_to_xml(self):
    data = {'custom_field': 'value'}
    xml = lib.buildXML(data)
    # Assert custom field appears in XML
```

---

## Adding a New CLI Command

### Step 1: Create Function in execHAL.py

```python
def myCommand(param1, param2=None, verbose=False, **kwargs):
    """Execute my command."""
    logger.debug(f"Running myCommand with {param1}")
    # ... implementation
    return os.EX_OK
```

### Step 2: Add to CLI Wrapper

Edit `src/push2HAL/push2hal.py`:

```python
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    
    # Add your command
    parser_mycommand = subparsers.add_parser('mycommand')
    parser_mycommand.add_argument('param1', help='...')
    parser_mycommand.add_argument('--param2', help='...')
    parser_mycommand.set_defaults(func=execHAL.myCommand)
```

### Step 3: Test from CLI

```bash
python -m push2HAL mycommand arg1 --param2 value
```

---

## Logging

Use `loguru` logger for all logging:

```python
from loguru import logger

logger.debug("Detailed diagnostic info")
logger.info("General information")
logger.warning("Warning condition")
logger.error("Error condition")
```

**Enable debug output:**

```bash
json2hal metadata.json -c ~/.apihal --verbose
```

**Log output goes to stderr** in standard format:

```
2024-01-15 10:30:45.123 | DEBUG    | PUSH2HAL | module:function:42 | Message here
```

---

## Error Handling

Use POSIX exit codes:

```python
import os

def my_function():
    if missing_config:
        logger.error("Missing configuration")
        return os.EX_CONFIG  # 78
    
    if file_not_found:
        logger.error("File not found")
        return os.EX_OSFILE  # 72
    
    if logic_error:
        logger.error("Invalid data")
        return os.EX_SOFTWARE  # 70
    
    return os.EX_OK  # 0
```

Exit codes are automatically propagated to shell:

```bash
json2hal missing.json; echo "Exit code: $?"  # Outputs: Exit code: 72
```

---

## Code Style

### Formatting

Use `black` for code formatting (if available):

```bash
black src/push2HAL/
```

### Naming Conventions

- **Classes:** PascalCase (`HALelt`, `Article`)
- **Functions:** snake_case (`build_xml`, `load_data`)
- **Constants:** UPPER_SNAKE_CASE (`DEFAULT_SERVER`, `HAL_TYPE`)
- **Private methods:** `_leading_underscore()`

### Docstrings

Use Google-style docstrings:

```python
def my_function(param1, param2):
    """Short one-line summary.
    
    Longer description if needed, spanning multiple lines.
    Explains behavior, edge cases, and examples.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When X condition
        OSError: When Y condition
    
    Example:
        >>> result = my_function('a', 'b')
        >>> print(result)
    """
```

---

## Release Process

### Version Bumping

Edit `pyproject.toml` and update `version`:

```toml
[project]
version = "1.2.3"
```

### Build Distribution

```bash
pip install build
python -m build
```

Creates `dist/push2HAL-1.2.3.tar.gz` and `.whl` files.

### Upload to PyPI

```bash
pip install twine
twine upload dist/push2HAL-1.2.3*
```

### Create GitHub Release

1. Push version bump commit to main
2. Create tag: `git tag v1.2.3`
3. Push tag: `git push origin v1.2.3`
4. Create release on GitHub with change notes

---

## Resources

- [lxml Documentation](https://lxml.de/)
- [Loguru Documentation](https://loguru.readthedocs.io/)
- [SWORD Protocol](http://www.swordapp.org/)
- [TEI Schema](https://tei-c.org/)
- [HAL Documentation](https://doc.archives-ouvertes.fr/)
