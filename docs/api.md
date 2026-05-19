# API Reference

## Core Classes

### HALelt

Base class for all HAL document types. Provides unified interface for loading, building, and uploading documents.

#### Constructor

```python
HALelt(data=None)
```

Create a new HAL element. Optionally loads initial data from dict or JSON file path.

**Parameters:**
- `data` (dict or str, optional): Document metadata as dict or path to JSON file

#### Class Methods

##### `from_type(typeDoc, data=None)`

Factory method to instantiate the correct HAL document subclass based on type.

**Parameters:**
- `typeDoc` (str): HAL document type code (e.g., 'article', 'book', 'thesis')
- `data` (dict or str, optional): Document metadata

**Returns:** Appropriate HALelt subclass instance

**Example:**
```python
doc = HALelt.from_type('article', {'title': {'en': 'Example'}})
assert isinstance(doc, Article)
```

##### `from_input(data)`

Build a HALelt from JSON content (dict or file path), automatically determining the document type.

**Parameters:**
- `data` (dict or str): Document metadata or JSON file path

**Returns:** Appropriate HALelt subclass instance

##### `fromXMLContent(xmlSource, data=None)`

Load an existing TEI XML document and infer its HAL type, optionally patching with new metadata.

**Parameters:**
- `xmlSource` (str, ElementTree, or Element): TEI XML source
- `data` (dict or str, optional): Additional metadata to merge

**Returns:** HALelt instance with type inferred from XML

**Example:**
```python
# Load existing TEI and preserve its type
doc = HALelt.fromXMLContent('hal-01234567.tei.xml')
# Update with new metadata while keeping original type
doc = HALelt.fromXMLContent('hal-01234567.tei.xml', 
                           data={'abstract': {'en': 'New abstract'}})
```

#### Instance Methods

##### `loadData(data)`

Load document metadata from dict or JSON file path.

**Parameters:**
- `data` (dict or str): Metadata dict or JSON file path

##### `loadXML(xmlSource)`

Load or set TEI XML content. Accepts file path, ElementTree, or Element.

**Parameters:**
- `xmlSource` (str, ElementTree, or Element): TEI XML source

##### `populate(data=None, inTree=None)`

Build/update the XML tree from metadata, injecting or preserving the document type.

**Parameters:**
- `data` (dict, optional): Metadata to populate (defaults to `self.data`)
- `inTree` (Element, optional): Existing XML tree to update

##### `prepare(dirPath, xmlFileName=None, pdf_path=None, options=None, hal_id=None)`

Prepare the upload payload (XML file and optional ZIP with PDF).

**Parameters:**
- `dirPath` (str): Output directory
- `xmlFileName` (str, optional): XML filename (default: `upload.xml`)
- `pdf_path` (str, optional): Path to PDF file
- `options` (dict, optional): HAL upload options
- `hal_id` (str, optional): HAL ID for update operations

**Returns:** Tuple of (sendfile_path, headers_dict)

##### `upload(credentials, server='preprod', dirPath=None, xmlFileName=None, pdf_path=None, options=None, hal_id=None)`

Prepare and upload the document to HAL.

**Parameters:**
- `credentials` (dict): HAL login credentials `{'login': '...', 'passwd': '...'}`
- `server` (str): Target server ('preprod' or 'prod')
- Other parameters same as `prepare()`

**Returns:** Status code or HAL ID on success

**Example:**
```python
doc = HALelt.from_input({'type': 'article', 'title': {'en': '...'}})
status = doc.upload(
    credentials={'login': 'user', 'passwd': 'pass'},
    server='preprod',
    dirPath='/tmp',
    pdf_path='article.pdf'
)
```

### Document Type Classes

Specialized subclasses for each HAL document type:

- **`Article`** (ART): Journal articles
- **`Book`** (OUV): Books and monographs
- **`BookChapter`** (COUV): Chapters in edited books
- **`Conference`** (COMM): Conference papers
- **`Thesis`** (THESE): Doctoral theses
- **`PhDThesis`** (THESE): PhD theses (alias for Thesis)
- **`MasterThesis`** (MEM): Master's theses
- **`HDR`** (HDR): Habilitation theses
- **`Poster`** (POSTER): Conference posters
- **`Proceedings`** (PROCEEDINGS): Edited proceedings
- **`ResearchReport`** (RESREPORT): Research reports
- **`TechnicalReport`** (TECHREPORT): Technical reports
- **`PrePrint`** (PREPRINT): Preprints
- **`Patent`** (PATENT): Patents
- **`Dataset`** (DATAPAPER): Data papers and datasets
- **`Software`** (SOFTWARE): Software and source code
- **`Video`** (VIDEO): Video media
- **`Sound`** (SON): Audio media
- **`Image`** (IMG): Still images
- And more—all mapped in the `_TYPE_TO_CLASS` dictionary

Each subclass has `HAL_TYPE` set to its canonical HAL code.

## Entry Point Functions

### runJSON2HAL(jsonContent, verbose=False, prod='preprod', credentials=None, completion=None, idhal=None)

Create a new HAL entry from JSON metadata.

**Parameters:**
- `jsonContent` (dict or str): Metadata dict or JSON file path
- `verbose` (bool): Enable debug logging
- `prod` (str): Server mode ('preprod', 'prod', or 'test')
- `credentials` (dict): HAL credentials
- `completion` (str): Grobid completion options
- `idhal` (str): Deposit on behalf of another user

**Returns:** Exit status code

### updateHAL(data=None, pdf_path=None, verbose=False, prod='preprod', credentials=None, completion=None, halid=None, idhal=None)

Update an existing HAL entry.

**Parameters:**
- `data` (dict): Metadata updates
- `pdf_path` (str): Optional PDF to upload
- `halid` (str): HAL ID to update (required)
- Other parameters same as `runJSON2HAL()`

**Returns:** Exit status code

### runPDF2HAL(pdf_path, verbose=False, prod='preprod', credentials=None, completion=None, halid=None, idhal=None, interaction=True)

Add a PDF to an existing HAL entry.

**Parameters:**
- `pdf_path` (str): Path to PDF file
- `interaction` (bool): Enable interactive mode
- `halid` (str): Target HAL ID (optional—will search if not provided)
- Other parameters same as `runJSON2HAL()`

**Returns:** Exit status code

## Utility Functions

### libHAL.getTypeDoc(typeDoc)

Resolve a document type string to its canonical HAL type code.

**Parameters:**
- `typeDoc` (str): Type name or code

**Returns:** Canonical HAL type code (e.g., 'ART', 'OUV') or None

### libHAL.buildXML(data, inTree=None)

Build TEI XML tree from metadata dict.

**Parameters:**
- `data` (dict): Document metadata
- `inTree` (Element, optional): Existing tree to update

**Returns:** Root Element of TEI tree

### libHAL.preparePayload(tei_content, pdf_path=None, dirPath=None, xmlFileName='upload.xml', hal_id=None, options=dict())

Prepare the upload payload (files and headers).

**Parameters:**
- `tei_content` (Element): TEI XML root element
- `pdf_path` (str, optional): PDF file to include
- `dirPath` (str): Output directory
- `xmlFileName` (str): Name for XML file
- `hal_id` (str, optional): HAL ID for updates
- `options` (dict): SWORD upload options

**Returns:** Tuple of (sendfile_path, headers_dict)

### libHAL.upload2HAL(file, headers=None, hal_id=None, credentials=None, server='preprod')

Upload file to HAL via SWORD protocol.

**Parameters:**
- `file` (str): Path to file (XML or ZIP)
- `headers` (dict): SWORD headers
- `hal_id` (str, optional): For updates
- `credentials` (dict): Login credentials
- `server` (str): Target server

**Returns:** HAL ID or status code

## Exit Status Codes

- `os.EX_OK` (0): Success
- `os.EX_CONFIG` (78): Configuration error (missing credentials, invalid options)
- `os.EX_OSFILE` (72): File system error (file not found, permission denied)
- `os.EX_SOFTWARE` (70): Software/logic error (invalid metadata, API errors)

## JSON Metadata Schema

See [Configuration](configuration.md) for the complete JSON schema and field documentation.
