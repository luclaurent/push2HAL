# push2HAL Documentation

**push2HAL** is a Python library and CLI tool suite for uploading academic documents to [HAL](https://hal.science), the French national open access repository. It handles metadata from JSON files and PDFs, builds valid TEI XML structures, and communicates with HAL's SWORD API for deposits.

## Overview

- **`json2hal`**: Create new HAL entries from JSON metadata files, with optional PDF uploads
- **`pdf2hal`**: Add PDF files to existing HAL entries
- **`push2hal`**: Multi-command interface for create, update, and PDF operations
- **Core library**: Object-oriented API for building, updating, and uploading HAL documents

## Quick Start

### Create a New HAL Entry

```bash
json2hal examples/test.json -c .apihal
```

### Add a PDF to an Existing Entry

```bash
pdf2hal path/to/document.pdf -a hal-01234567 -c .apihal
```

### Update an Existing Entry

```bash
push2hal update -c .apihal --halid hal-01234567
```

## Documentation Structure

- [API Reference](api.md) — Detailed class and function documentation
- [Architecture](architecture.md) — System design and data flow
- [Workflows](workflows.md) — Common usage patterns and examples
- [Configuration](configuration.md) — Credentials, options, and defaults
- [Development](development.md) — Contributing, testing, and extending

## Installation

Install from PyPI:

```bash
pip install push2HAL
```

Or from source:

```bash
cd /path/to/push2HAL
pip install .
```

## Requirements

- Python 3.8+
- See `pyproject.toml` for full dependency list

## Key Concepts

### HAL Document Types

`push2HAL` supports all HAL document types through the `HALelt` class hierarchy:

- **Articles**: `Article`, `DataPaper`, `BookReview`
- **Theses**: `Thesis`, `PhDThesis`, `MasterThesis`, `HDR`
- **Reports**: `ResearchReport`, `TechnicalReport`, `Report`
- **Media**: `Video`, `Sound`, `Image`, `Photography`, etc.
- And many others—see [API Reference](api.md) for the complete list

### JSON Metadata Schema

Documents are defined in JSON with fields like:

```json
{
  "type": "article",
  "title": {"en": "Paper Title", "fr": "Titre du papier"},
  "authors": [{"firstname": "John", "lastname": "Doe", "affiliation": "..."}],
  "abstract": {"en": "...", "fr": "..."},
  "file": "document.pdf"
}
```

See [Configuration](configuration.md) for the complete schema.

### TEI XML

All documents are converted to TEI (Text Encoding Initiative) XML conforming to the [HAL TEI profile](https://hal.archives-ouvertes.fr/documents/aofr.xsd), then uploaded via the SWORD protocol.

## Credentials

Store HAL credentials in `.apihal` (in your home directory or project root):

```json
{
  "login": "your-username",
  "passwd": "your-password"
}
```

Alternatively, pass credentials via command-line arguments:

```bash
json2hal file.json -l username -p password
```

## Next Steps

- Read [Workflows](workflows.md) for usage examples
- Check [API Reference](api.md) for Python library usage
- See [Architecture](architecture.md) to understand the system design
