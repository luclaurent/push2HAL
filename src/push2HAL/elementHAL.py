####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************

"""HAL Document Object Model

This module provides the core object model for representing HAL (Hyper Articles en Ligne) archive
documents. It implements an object-oriented interface for building, updating, and uploading academic
documents to the HAL repository via the SWORD protocol.

The main class is HALelt, an abstract base class representing a generic HAL document. Document-type-specific
subclasses (Article, Thesis, Book, etc.) reflect the HAL archive's document taxonomy. Each class is lightweight,
delegating XML construction to libHAL and API communication to libAPIHAL.

Key Features:
  - Type-based factory methods (from_type, from_input, fromXMLContent) for flexible instantiation
  - Unified interface for loading metadata (JSON dict or file), XML (file or element tree), and uploading
  - Type inference from existing TEI XML to preserve document classification during updates
  - Support for all 40+ HAL document types via a type dispatch table

Typical Usage:
  # Create new article from JSON
  doc = HALelt.from_input('metadata.json')
  status = doc.upload(credentials={'login': '...', 'passwd': '...'}, server='preprod')

  # Update existing entry in HAL
  doc = HALelt.fromXMLContent('hal-01234567.tei.xml', data={'abstract': {'en': '...'}})
  status = doc.upload(credentials=..., server='preprod')

References:
  - https://github.com/CCSDForge/HAL/blob/master/schema/Readme.md
  - https://hal.archives-ouvertes.fr/
"""

from abc import ABC
from loguru import logger
import json
import os
import lxml.etree as etree

from . import libHAL as lib
from . import misc as m
from . import default as dflt


class HALelt(ABC):
    """Abstract base class for HAL document elements.
    
    Represents a single document in the HAL archive. Provides unified interface for:
      1. Loading metadata (JSON dict or file path)
      2. Loading or building TEI XML
      3. Preparing upload payloads (files and SWORD headers)
      4. Uploading to HAL via SWORD protocol
    
    Each subclass (Article, Thesis, etc.) specifies its HAL_TYPE constant and inherits all
    functionality from HALelt. Factory methods (from_type, from_input, fromXMLContent) automatically
    select the correct subclass.
    
    Attributes:
        data (dict): Metadata as Python dict (in-memory, mutable)
        dataJSON (str): Serialized metadata as JSON string (for debugging/export)
        dataXML (lxml.etree.Element): TEI XML root element (for SWORD submission)
        dataHAL (dict): Response from HAL after upload (populated on successful upload)
        HAL_TYPE (str): Canonical HAL document type code (e.g., 'ART', 'OUV'). Set per subclass.
    
    Example:
        >>> doc = HALelt.from_type('article', {'title': {'en': 'Example'}})
        >>> assert isinstance(doc, Article)
        >>> doc.upload(credentials={'login': 'user', 'passwd': '...'})
    """

    HAL_TYPE = None  # override in subclasses

    def __init__(self, data=None):
        """Initialize a HAL element with optional metadata.
        
        Args:
            data (dict or str, optional): Document metadata as Python dict or path to JSON file.
                If provided, automatically calls loadData() to populate self.data and trigger populate().
        
        Raises:
            FileNotFoundError: If data is a string but file does not exist (logged, not raised).
            json.JSONDecodeError: If JSON file is invalid (logged, not raised).
        """
        self.data = None
        self.dataJSON = None
        self.dataXML = None
        self.dataHAL = None

        # Load data if provided
        if data is not None:
            self.loadData(data)

    def loadData(self, data):
        """Load metadata from a dict or from a JSON file path.
        
        Populates self.data and self.dataJSON. Automatically calls populate() to build
        the TEI XML tree (self.dataXML) from the metadata.
        
        Args:
            data (dict or str): Metadata as Python dict or path to JSON file.
        
        Raises:
            None (errors logged to logger instead of raised).
        
        Example:
            >>> doc = HALelt()
            >>> doc.loadData({'type': 'article', 'title': {'en': 'Example'}})
            >>> assert doc.data is not None
            >>> assert doc.dataXML is not None
        """
        if isinstance(data, dict):
            self.data = data
        elif isinstance(data, str) and os.path.isfile(data):
            with open(data, "r", encoding="utf-8") as f:
                self.data = json.loads(f.read())
        else:
            logger.error("Invalid data: expected a dict or a path to a JSON file")
            return
        self.dataJSON = json.dumps(self.data, indent=2)
        self.populate(self.data)

    def loadXML(self, xmlSource):
        """Load or set TEI XML content from various sources.
        
        Accepts file path (string), ElementTree, or Element root. Sets self.dataXML
        to the root Element. Useful for loading existing HAL entries for updates.
        
        Args:
            xmlSource (str, ElementTree, or Element): TEI XML source. Can be:
                - File path (str): Parsed with lxml.etree.parse()
                - ElementTree: Extracts root element
                - Element: Used directly as root
        
        Raises:
            OSError: File not found (logged, not raised).
            etree.XMLSyntaxError: Invalid XML (logged, not raised).
        
        Example:
            >>> doc = HALelt()
            >>> doc.loadXML('existing_entry.tei.xml')
            >>> assert doc.dataXML is not None
        """
        if isinstance(xmlSource, str):
            try:
                tree = etree.parse(xmlSource)
                self.dataXML = tree.getroot()
                logger.debug("XML loaded from {}".format(xmlSource))
            except (OSError, etree.XMLSyntaxError) as e:
                logger.error("Failed to load XML from {}: {}".format(xmlSource, e))
            return
        if hasattr(xmlSource, "getroot"):
            # ElementTree object
            self.dataXML = xmlSource.getroot()
            return
        if xmlSource is not None:
            # Assume it's an Element already
            self.dataXML = xmlSource

    def get_existing_type(self, xmlRoot=None):
        """Extract the existing HAL document type from a TEI XML tree.
        
        Queries the classCode[@scheme='halTypology'] element to find the @n attribute,
        which contains the HAL type code (e.g., 'ART', 'OUV'). Used during updates to
        preserve the original document type unless explicitly overridden.
        
        Args:
            xmlRoot (Element, optional): TEI XML root element. Defaults to self.dataXML.
        
        Returns:
            str: HAL type code (e.g., 'ART') or None if not found.
        
        Example:
            >>> doc = HALelt.fromXMLContent('hal-01234567.tei.xml')
            >>> existing_type = doc.get_existing_type()
            >>> assert existing_type == 'ART'
        """
        if xmlRoot is None:
            xmlRoot = self.dataXML
        if xmlRoot is None or not hasattr(xmlRoot, "xpath"):
            return None
        # Search for classCode element with halTypology scheme
        matches = xmlRoot.xpath(
            ".//*[local-name()='classCode' and @scheme='halTypology']"
        )
        if not matches:
            return None
        return matches[0].attrib.get("n")

    def populate(self, data=None, inTree=None):
        """Build or update the TEI XML tree from metadata dict.
        
        Injects the document type (from HAL_TYPE or existing XML) and calls libHAL.buildXML()
        to construct the complete TEI structure. Sets self.dataXML.
        
        Type Priority (when building XML):
          1. Explicit type in data dict (if provided)
          2. Class-level HAL_TYPE (from subclass)
          3. Existing type in inTree (preserved from existing XML)
          4. None (will trigger validation error or default to OTHER)
        
        Args:
            data (dict, optional): Metadata to populate. Defaults to self.data.
            inTree (Element, optional): Existing XML tree to update. Defaults to self.dataXML.
                If provided, updates existing tree instead of creating new one.
        
        Returns:
            None (updates self.dataXML in-place).
        
        Raises:
            None (errors logged but not raised).
        
        Example:
            >>> doc = Article({'title': {'en': 'Test'}})
            >>> doc.populate()
            >>> assert 'ART' in etree.tostring(doc.dataXML)
        """
        if data is None:
            data = self.data
        if data is None:
            logger.error("No data to populate")
            return
        # inject document type from class attribute if not already set
        populated = dict(data)
        if inTree is None:
            inTree = self.dataXML
        if not populated.get("type"):
            populated["type"] = self.HAL_TYPE or self.get_existing_type(inTree)
        self.dataXML = lib.buildXML(populated, inTree)

    def writeJSON(self, filename):
        """Write metadata to JSON file.
        
        Args:
            filename (str): Output file path.
        
        Raises:
            IOError: File write error (logged, not raised).
        """
        if self.dataJSON is None:
            logger.error("No JSON data to write")
            return
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.dataJSON)
        logger.debug("JSON written to {}".format(filename))

    def writeXML(self, filename):
        """Write TEI XML to file.
        
        Args:
            filename (str): Output file path.
        
        Raises:
            IOError: File write error (logged, not raised).
        """
        if self.dataXML is None:
            logger.error("No XML data to write")
            return
        m.writeXML(self.dataXML, filename)

    @classmethod
    def from_type(cls, typeDoc, data=None):
        """Factory: Instantiate the correct HALelt subclass for a given HAL document type.
        
        Resolves a type name (case-insensitive) to a canonical HAL type code, then looks up
        the corresponding subclass in the _TYPE_TO_CLASS mapping. Falls back to Other if type
        is unknown.
        
        Args:
            typeDoc (str): Document type name or code. Examples: 'article', 'ART', 'book', 'OUV'.
            data (dict or str, optional): Metadata to pass to the subclass constructor.
        
        Returns:
            HALelt: Instance of appropriate subclass (e.g., Article, Thesis) or Other.
        
        Example:
            >>> doc = HALelt.from_type('article', {'title': {'en': '...'}})
            >>> assert isinstance(doc, Article)
            >>> doc2 = HALelt.from_type('ART')  # Same result
        """
        halCode = lib.getTypeDoc(typeDoc)
        klass = Other if halCode is None else _TYPE_TO_CLASS.get(halCode, Other)
        return klass(data)

    @classmethod
    def from_input(cls, data):
        """Factory: Build HALelt from metadata dict or JSON file path.
        
        Automatically detects document type from the 'type' field in JSON and instantiates
        the appropriate subclass. If type is missing, falls back to from_type with None.
        
        Args:
            data (dict or str): Metadata as dict or path to JSON file.
        
        Returns:
            HALelt: Appropriate subclass instance with data loaded.
        
        Raises:
            None (errors logged, returns empty instance of cls).
        
        Example:
            >>> doc = HALelt.from_input({'type': 'article', 'title': {'en': '...'}})
            >>> assert isinstance(doc, Article)
            >>> doc2 = HALelt.from_input('metadata.json')  # Load from file
        """
        if isinstance(data, dict):
            return cls.from_type(data.get("type"), data=data)
        if isinstance(data, str) and os.path.isfile(data):
            with open(data, "r", encoding="utf-8") as f:
                parsed = json.loads(f.read())
            return cls.from_type(parsed.get("type"), data=parsed)
        logger.error("Invalid data: expected a dict or a path to a JSON file")
        return cls()

    @classmethod
    def fromXMLContent(cls, xmlSource, data=None):
        """Factory: Load existing TEI XML and infer the best HALelt subclass from it.
        
        Loads TEI XML, extracts the existing HAL document type, instantiates the corresponding
        subclass, and optionally merges new metadata. Useful for update workflows where existing
        type must be preserved.
        
        Type Inference: Reads classCode[@scheme='halTypology']/@n from the TEI to determine
        the document type (e.g., 'ART', 'OUV'). This preserves the original classification
        even if updating with different fields.
        
        Args:
            xmlSource (str, ElementTree, or Element): TEI XML source (file path or element tree).
            data (dict or str, optional): Additional metadata to merge. If type is present in
                data, it is ignored; the XML type is preserved.
        
        Returns:
            HALelt: Appropriate subclass instance with XML loaded and data merged (if provided).
        
        Example:
            >>> # Update workflow: preserve existing type
            >>> doc = HALelt.fromXMLContent('hal-01234567.tei.xml',
            ...                             data={'abstract': {'en': 'New abstract'}})
            >>> # doc type is inferred from XML; data updates are merged
        """
        probe = cls.__new__(cls)
        HALelt.__init__(probe)
        probe.loadXML(xmlSource)
        hal_type = probe.get_existing_type()
        instance = cls.from_type(hal_type)
        instance.loadXML(probe.dataXML)
        if data is not None:
            instance.loadData(data)
        return instance

    def prepare(self, dirPath, xmlFileName=None, pdf_path=None, options=None, hal_id=None):
        """Prepare the upload payload: write files and build SWORD headers.
        
        Writes TEI XML to disk. If PDF is provided, creates a ZIP archive containing both XML
        and PDF. Generates SWORD headers (metadata headers for HAL).
        
        Args:
            dirPath (str): Output directory for XML and/or ZIP files.
            xmlFileName (str, optional): Name for XML file. Defaults to 'upload.xml'.
            pdf_path (str, optional): Path to PDF file to include. If not provided, looks for
                'file' key in self.data.
            options (dict, optional): SWORD upload options (e.g., for Grobid processing).
                Defaults to {}.
            hal_id (str, optional): HAL ID for updates (includes in SWORD headers).
        
        Returns:
            tuple: (sendfile_path, headers_dict) ready for upload2HAL(). 
                - sendfile_path (str): Path to XML file or ZIP archive
                - headers_dict (dict): SWORD headers for HTTP request
                Returns (None, None) if XML is missing.
        
        Raises:
            None (errors logged but not raised).
        
        Example:
            >>> doc = HALelt.from_input('metadata.json')
            >>> sendfile, headers = doc.prepare('/tmp', pdf_path='article.pdf')
            >>> # sendfile is either '/tmp/upload.xml' or '/tmp/upload.zip'
        """
        if self.dataXML is None:
            logger.error("No XML data: call populate() or loadData() first")
            return None, None
        if options is None:
            options = {}
        if xmlFileName is None:
            xmlFileName = dflt.DEFAULT_UPLOAD_FILE_NAME_XML
        pdf_path = self.resolve_pdf_path(pdf_path=pdf_path, dirPath=dirPath)
        return lib.preparePayload(
            self.dataXML,
            pdf_path=pdf_path,
            dirPath=dirPath,
            xmlFileName=xmlFileName,
            hal_id=hal_id,
            options=options,
        )

    def upload(
        self,
        credentials=None,
        server="preprod",
        dirPath=None,
        xmlFileName=None,
        pdf_path=None,
        options=None,
        hal_id=None,
    ):
        """Prepare and upload the document to HAL via SWORD protocol.
        
        Calls prepare() to build payload, then upload2HAL() to submit to HAL. Handles
        credential validation and server selection (preprod/prod/test).
        
        Args:
            credentials (dict): HAL login credentials {'login': '...', 'passwd': '...'}.
                Required; if missing, returns EX_CONFIG.
            server (str): Target server ('preprod', 'prod', or 'test'). Default: 'preprod'.
            dirPath (str, optional): Output directory for XML/ZIP (default: current directory).
            xmlFileName (str, optional): XML filename (default: 'upload.xml').
            pdf_path (str, optional): PDF file to include (optional).
            options (dict, optional): SWORD options.
            hal_id (str, optional): HAL ID for updates (uploads to existing entry instead of creating new).
        
        Returns:
            int: Exit status code (os.EX_OK=0 on success; os.EX_CONFIG=78, os.EX_SOFTWARE=70 on error).
        
        Raises:
            None (errors caught, logged, and converted to exit code).
        
        Example:
            >>> doc = HALelt.from_input('metadata.json')
            >>> status = doc.upload(
            ...     credentials={'login': 'user', 'passwd': '...'},
            ...     server='preprod',
            ...     pdf_path='article.pdf'
            ... )
            >>> print(f"Upload status: {status}")
        """
        if not credentials:
            logger.error("No provided credentials")
            return os.EX_CONFIG
        sendfile, payload = self.prepare(
            dirPath=dirPath,
            xmlFileName=xmlFileName,
            pdf_path=pdf_path,
            options=options,
            hal_id=hal_id,
        )
        if sendfile is None:
            return os.EX_SOFTWARE
        status = lib.upload2HAL(
            sendfile,
            headers=payload,
            hal_id=hal_id,
            credentials=credentials,
            server=server,
        )
        return lib.manageError(status)

    def resolve_pdf_path(self, pdf_path=None, dirPath=None):
        """Resolve PDF file path from explicit argument, data dict, or working directory.
        
        Checks multiple sources in order:
          1. Explicit pdf_path parameter
          2. self.data['file'] field (if dict)
          3. Relative to dirPath (if provided)
          4. Relative to current directory
        
        Args:
            pdf_path (str, optional): Explicit PDF file path.
            dirPath (str, optional): Directory to resolve relative paths against.
        
        Returns:
            str: Absolute path to PDF file if found, None otherwise.
        
        Raises:
            None (error logged, returns None).
        
        Example:
            >>> doc = HALelt.from_input({'file': 'article.pdf', ...})
            >>> path = doc.resolve_pdf_path()
            >>> assert path is not None
        """
        candidate = pdf_path
        if candidate is None and isinstance(self.data, dict):
            candidate = self.data.get("file")
        if candidate is None:
            return None
        candidates = [candidate]
        if dirPath and not os.path.isabs(candidate):
            candidates.append(os.path.join(dirPath, candidate))
        for current in candidates:
            if os.path.isfile(current):
                logger.debug("PDF file: {}".format(current))
                return current
        logger.error("PDF file not found")
        return None

    @classmethod
    def fromXML(cls, filename):
        """Load an existing TEI XML file into a HALelt instance (XML only, no metadata dict).
        
        Convenience alias for fromXMLContent(filename) with no data parameter.
        Useful when you only have XML and don't want to provide metadata.
        
        Args:
            filename (str): Path to TEI XML file.
        
        Returns:
            HALelt: Appropriate subclass instance with XML loaded.
        
        Example:
            >>> doc = HALelt.fromXML('hal-01234567.tei.xml')
            >>> # doc can be updated or re-uploaded as-is
        """
        return cls.fromXMLContent(filename)


class Article(HALelt):
    """Journal article or scientific publication."""
    HAL_TYPE = "ART"

class Book(HALelt):
    """Book or monograph."""
    HAL_TYPE = "OUV"

class BookChapter(HALelt):
    """Chapter in an edited book."""
    HAL_TYPE = "COUV"

class BookReview(HALelt):
    """Review of a published book."""
    HAL_TYPE = "BOOKREVIEW"

class DataPaper(HALelt):
    """Dataset paper describing research data."""
    HAL_TYPE = "DATAPAPER"

class Poster(HALelt):
    """Conference poster."""
    HAL_TYPE = "POSTER"

class Proceedings(HALelt):
    """Conference proceedings or edited collection."""
    HAL_TYPE = "PROCEEDINGS"

class Manual(HALelt):
    """Software manual or user guide."""
    HAL_TYPE = "MANUAL"

class Critique(HALelt):
    """Critical article or commentary."""
    HAL_TYPE = "CRIT"

class SynthWork(HALelt):
    """Synthesis work or survey."""
    HAL_TYPE = "SYNTOUV"

class Dictionary(HALelt):
    """Dictionary or encyclopedia."""
    HAL_TYPE = "DICTIONARY"

class Blog(HALelt):
    """Blog post or online commentary."""
    HAL_TYPE = "BLOG"

class Dataset(HALelt):
    """Research dataset or data collection."""
    HAL_TYPE = "DATAPAPER"

class Software(HALelt):
    """Software or computer program."""
    HAL_TYPE = "SOFTWARE"

class Notice(HALelt):
    """Notice or announcement."""
    HAL_TYPE = "NOTICE"

class Translation(HALelt):
    """Translated work."""
    HAL_TYPE = "TRAD"

class Undefined(HALelt):
    """Undefined or other document type."""
    HAL_TYPE = "UNDEFINED"

class PrePrint(HALelt):
    """Preprint or working paper."""
    HAL_TYPE = "PREPRINT"

class ReportChapter(HALelt):
    """Chapter in a research or technical report."""
    HAL_TYPE = "CREPORT"

class ResearchReport(HALelt):
    """Research report."""
    HAL_TYPE = "RESREPORT"

class TechnicalReport(HALelt):
    """Technical report."""
    HAL_TYPE = "TECHREPORT"

class Conference(HALelt):
    """Conference paper."""
    HAL_TYPE = "COMM"

class Patent(HALelt):
    """Patent or patent application."""
    HAL_TYPE = "PATENT"

class Report(HALelt):
    """General report."""
    HAL_TYPE = "REPORT"

class Thesis(HALelt):
    """Doctoral thesis or PhD thesis."""
    HAL_TYPE = "THESE"

class HDR(HALelt):
    """Habilitation thesis (Habilitation à Diriger des Recherches)."""
    HAL_TYPE = "HDR"

class PhDThesis(HALelt):
    """PhD thesis (alias for Thesis)."""
    HAL_TYPE = "THESE"

class MasterThesis(HALelt):
    """Master's thesis or equivalent."""
    HAL_TYPE = "MEM"

class Image(HALelt):
    """Still image or photograph."""
    HAL_TYPE = "IMG"

class Photography(HALelt):
    """Photograph or photographic work."""
    HAL_TYPE = "PHOTOGRAPHY"

class Drawing(HALelt):
    """Drawing or sketch."""
    HAL_TYPE = "DRAWING"

class Illustration(HALelt):
    """Illustration or graphic."""
    HAL_TYPE = "ILLUSTRATION"

class Engraving(HALelt):
    """Engraving or print."""
    HAL_TYPE = "GRAVURE"

class Graphics(HALelt):
    """Graphics or design work."""
    HAL_TYPE = "GRAPHICS"

class Video(HALelt):
    """Video or audiovisual recording."""
    HAL_TYPE = "VIDEO"

class Sound(HALelt):
    """Audio recording or sound file."""
    HAL_TYPE = "SON"

class DocConf(HALelt):
    """Conference presentation or proceedings paper."""
    HAL_TYPE = "PRESCONF"

class Note(HALelt):
    """Note or research note."""
    HAL_TYPE = "NOTE"

class ActivityReport(HALelt):
    """Activity or annual report."""
    HAL_TYPE = "REPACT"

class Synthesis(HALelt):
    """Synthesis or summary document."""
    HAL_TYPE = "SYNTHESE"

class Other(HALelt):
    """Other or miscellaneous document type."""
    HAL_TYPE = "OTHER"


# Type dispatch table: Canonical HAL code -> HALelt subclass
# Maps all known HAL type codes to their corresponding Python classes
# Used by from_type() factory for dynamic class instantiation
_TYPE_TO_CLASS = {
    "ART":         Article,
    "ARTREV":      Article,
    "DATAPAPER":   DataPaper,
    "BOOKREVIEW":  BookReview,
    "COMM":        Conference,
    "POSTER":      Poster,
    "PROCEEDINGS": Proceedings,
    "ISSUE":       Proceedings,
    "OUV":         Book,
    "CRIT":        Critique,
    "MANUAL":      Manual,
    "SYNTOUV":     SynthWork,
    "DICTIONARY":  Dictionary,
    "COUV":        BookChapter,
    "BLOG":        Blog,
    "NOTICE":      Notice,
    "TRAD":        Translation,
    "PATENT":      Patent,
    "OTHER":       Other,
    "UNDEFINED":   Undefined,
    "PREPRINT":    PrePrint,
    "WORKINGPAPER": PrePrint,
    "CREPORT":     ReportChapter,
    "REPORT":      Report,
    "RESREPORT":   ResearchReport,
    "TECHREPORT":  TechnicalReport,
    "FUNDREPORT":  Report,
    "EXPERTREPORT": Report,
    "DMP":         Report,
    "THESE":       Thesis,
    "HDR":         HDR,
    "LECTURE":     Other,
    "MEM":         MasterThesis,
    "MEMLIC":      MasterThesis,
    "IMG":         Image,
    "PHOTOGRAPHY": Photography,
    "DRAWING":     Drawing,
    "ILLUSTRATION": Illustration,
    "GRAVURE":     Engraving,
    "GRAPHICS":    Graphics,
    "VIDEO":       Video,
    "SON":         Sound,
    "SOFTWARE":    Software,
    "PRESCONF":    DocConf,
    "ETABTHESE":   PhDThesis,
    "NOTE":        Note,
    "OTHERREPORT": Report,
    "REPACT":      ActivityReport,
    "SYNTHESE":    Synthesis,
}
