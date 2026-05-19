# Architecture

## System Overview

**push2HAL** follows a layered architecture with clear separation between:

1. **CLI Entry Points**: User-facing command-line tools
2. **Orchestration Layer**: High-level workflow functions
3. **Object Model**: Core HALelt classes
4. **XML/SWORD Layer**: TEI building and HAL API communication
5. **Utilities**: Helper functions for I/O, validation, and conversion

```
┌─────────────────────────────────────────────┐
│  CLI Tools (json2hal, pdf2hal, push2hal)    │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Orchestration (execHAL module)             │
│  - runJSON2HAL()                             │
│  - updateHAL()                               │
│  - runPDF2HAL()                              │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Object Model (elementHAL.HALelt)           │
│  - from_input(), from_type()                 │
│  - fromXMLContent()                          │
│  - loadData(), populate()                    │
│  - prepare(), upload()                       │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  XML & SWORD Layer (libHAL module)           │
│  - buildXML() — TEI tree construction        │
│  - preparePayload() — ZIP/headers prep       │
│  - upload2HAL() — SWORD communication        │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Utilities                                   │
│  - misc: file I/O, XML validation            │
│  - libAPIHAL: HAL search/retrieval           │
│  - default: constants and config             │
└─────────────────────────────────────────────┘
```

## Data Flow

### Create New Entry (json2hal)

```
JSON Input
    ↓
HALelt.from_input() — Parse JSON, detect type, instantiate subclass
    ↓
HALelt.loadData() — Set metadata fields
    ↓
HALelt.populate() — Build TEI XML tree
    ↓
libHAL.buildXML() — Generate complete TEI document
    ↓
HALelt.prepare() — Write files, create ZIP with optional PDF
    ↓
libHAL.preparePayload() — Build SWORD headers
    ↓
HALelt.upload() → libHAL.upload2HAL() — SWORD POST to HAL
    ↓
Return HAL ID or error code
```

### Update Entry (updateHAL)

```
HAL ID + Update Data
    ↓
libAPIHAL.search() — Retrieve existing TEI from HAL
    ↓
HALelt.fromXMLContent() — Load TEI, infer type, preserve HAL metadata
    ↓
HALelt.loadData() — Merge new metadata (type preserved if not specified)
    ↓
libHAL.buildXML() — Regenerate TEI with updates
    ↓
[Same as Create: prepare() → upload()]
    ↓
Return status (200/202 = success)
```

### Add PDF (pdf2hal)

```
PDF File
    ↓
m.extract_info() — Extract title via pdfplumber
    ↓
IF no HAL ID: Search HAL for matching title → choose result
    ↓
libAPIHAL.search() — Retrieve TEI for HAL ID
    ↓
HALelt.fromXMLContent() — Load TEI (empty data dict)
    ↓
HALelt.prepare(pdf_path=...) — Include PDF in payload
    ↓
libHAL.preparePayload() → HALelt.upload()
    ↓
Return status
```

## Key Design Decisions

### Object-Oriented Model

**Why:** The `HALelt` class hierarchy reflects HAL's document type taxonomy, enabling type-specific behavior and clean dispatch.

- Each document type (Article, Thesis, etc.) is a subclass
- `from_type()` factory automatically selects the correct subclass
- Subclasses can override behavior for type-specific fields

### Unified Data/XML Interface

**Why:** Separating JSON data, serialized JSON, and TEI XML allows flexible workflows:

- `data`: Python dict (in-memory manipulation)
- `dataJSON`: Serialized JSON (debugging, export)
- `dataXML`: TEI XML Element (SWORD/HAL submission)

This tri-state design supports:
- Load-modify-save workflows (update)
- JSON→XML conversion (create)
- XML→update workflows (preserve existing structure)

### Lazy Type Inference

**Why:** When updating, preserve the original HAL type unless explicitly overridden:

- Retrieve existing TEI → `get_existing_type()` extracts `@n` attribute from `classCode[@scheme='halTypology']`
- If user provides `type` in update JSON, use that; else keep original
- Prevents accidental downgrading (e.g., Article → Other)

### SWORD/API Abstraction

**Why:** Low-level XML/SWORD logic (`libHAL`) stays independent of object model:

- `HALelt` orchestrates but doesn't implement XML building
- `libHAL` functions are reusable by other tools/scripts
- Easy to upgrade SWORD implementation or XML schema

## Module Breakdown

### elementHAL

Object model for HAL documents. Contains:

- `HALelt` base class
- 40+ document type subclasses
- Type dispatch table (`_TYPE_TO_CLASS`)
- Core methods: load, populate, prepare, upload

### execHAL

High-level orchestration for CLI entry points. Contains:

- `runJSON2HAL()` — Create flow
- `updateHAL()` — Update flow
- `runPDF2HAL()` — PDF upload flow
- Helper functions for JSON loading, option building, PDF resolution
- Server mode selection, logging setup

### libHAL

Low-level XML and SWORD operations. Contains:

- `buildXML()` — TEI tree construction from metadata
- Per-field functions (`setTitles`, `setAuthors`, `setAbstract`, etc.)
- `preparePayload()` — File prep and SWORD header generation
- `upload2HAL()` — HTTP SWORD POST/PUT
- Type resolution (`getTypeDoc()`)
- ZIP building for XML+PDF uploads

### libAPIHAL

HAL API communication. Contains:

- `APIHAL` class — Search documents
- `APIHALauthor`, `APIHALstructure`, etc. — Query other HAL endpoints
- `directAccess()` — Fetch document by HAL ID in various formats
- Query building and result parsing

### misc

Utility functions:

- `writeXML()` — File I/O with TEI validation
- `checkXML()` — XSD validation
- `extract_info()` — PDF metadata extraction
- `load_credentials()` — Credentials from file/args/env
- Header adaptation functions

### default

Constants and configuration:

- HAL API URLs (preprod, prod)
- Default filenames, namespaces, SWORD options
- Validation schema paths
- Return format mappings

### json2hal, pdf2hal, push2hal

CLI entry points. Each:

- Parses command-line arguments
- Calls appropriate `execHAL` function
- Passes through credentials, options, logging flags
- Exits with standard status codes

## Error Handling

Exit codes follow POSIX conventions:

| Code | Name | Meaning |
|------|------|---------|
| 0 | EX_OK | Success |
| 70 | EX_SOFTWARE | Logic/runtime error (invalid metadata, API failure) |
| 72 | EX_OSFILE | File system error (missing file, permission denied) |
| 78 | EX_CONFIG | Configuration error (missing credentials, bad options) |

Invalid metadata is caught during `buildXML()` (e.g., bad ISSN) but logged as warning; upload is attempted anyway to allow HAL to validate further.

## Extension Points

To add custom behavior:

1. **New document type**: Subclass `HALelt` with custom `HAL_TYPE`, add to `_TYPE_TO_CLASS`
2. **Custom metadata fields**: Update `libHAL.buildXML()` with new `set*` function and call it
3. **New validation**: Extend `misc.checkXML()` or add validation in `HALelt.populate()`
4. **CLI commands**: Add function in `execHAL`, wire up in `push2hal.py`
