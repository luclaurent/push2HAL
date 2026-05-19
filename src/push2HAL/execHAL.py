####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************

"""High-Level Workflow Orchestration for push2HAL

This module provides entry-point functions for the three main workflows:
  1. runJSON2HAL() — Create a new HAL entry from JSON metadata
  2. updateHAL() — Update an existing HAL entry with new metadata or PDF
  3. runPDF2HAL() — Add a PDF to an existing HAL entry

Each function handles credential validation, server selection (preprod/prod/test),
directory setup, and delegates to the HALelt object model for actual XML building and upload.

Typical usage from CLI tools or other scripts:
  status = runJSON2HAL('metadata.json', 
                       credentials={'login': '...', 'passwd': '...'})
  status = updateHAL(data={'abstract': {...}}, 
                     halid='hal-01234567',
                     credentials={...})
  status = runPDF2HAL('article.pdf', 
                      halid='hal-01234567',
                      credentials={...})
"""

import os
import sys
import json
from loguru import logger

from . import libAPIHAL as libAPI
from . import elementHAL as elt
from . import misc as m
from . import default as dflt


def _load_json_input(jsonContent):
    """Load JSON content from dict or JSON file path. Internal helper.
    
    Returns (data_dict, directory, xml_filename) tuple or (None, None, None) if error.
    
    Args:
        jsonContent (dict or str): Metadata dict or path to JSON file.
    
    Returns:
        tuple: (dataJSON, dirPath, xml_name) or (None, None, None) on error.
    """
    if isinstance(jsonContent, dict):
        dirPath = os.path.join(os.getcwd(), "tmp")
        logger.debug("Directory: {}".format(dirPath))
        os.makedirs(dirPath, exist_ok=True)
        return jsonContent, dirPath, dflt.DEFAULT_UPLOAD_FILE_NAME_XML

    if os.path.isfile(jsonContent):
        logger.debug("JSON file: {}".format(jsonContent))
        dirPath = os.path.dirname(jsonContent)
        logger.debug("Directory: {}".format(dirPath))
        with open(jsonContent, "r", encoding="utf-8") as f:
            dataJSON = json.loads(f.read())
        xml_name = os.path.basename(jsonContent).replace(".json", ".xml")
        return dataJSON, dirPath, xml_name

    logger.error("JSON file not found")
    return None, None, None


def _build_upload_options(completion=None, idhal=None, testMode=False):
    """Build HAL SWORD upload options dict. Internal helper.
    
    Args:
        completion (str, optional): Grobid completion option string.
        idhal (str, optional): HAL username for deposit-on-behalf-of.
        testMode (bool): Enable test mode flag (1=test, 0=prod).
    
    Returns:
        dict: SWORD options for upload.
    """
    options = {}
    if completion:
        logger.info(
            "Specific completion option(s) will be used: {}".format(completion)
        )
        options["completion"] = completion
    if idhal:
        logger.info("Deposit on behalf of: {}".format(idhal))
        options["idFrom"] = idhal
    options["testMode"] = "1" if testMode else "0"
    return options


def _resolve_document_pdf(document, dirPath=None, pdf_path=None):
    """Resolve the PDF path from explicit argument or document data. Internal helper.
    
    Args:
        document (HALelt): Document object.
        dirPath (str, optional): Directory to resolve relative paths.
        pdf_path (str, optional): Explicit PDF path.
    
    Returns:
        str: Resolved PDF path or None if not found/expected.
    """
    resolved_path = document.resolve_pdf_path(pdf_path=pdf_path, dirPath=dirPath)
    expected_pdf = pdf_path is not None or document.data.get("file", None)
    if expected_pdf and resolved_path is None:
        return None
    return resolved_path



def runJSON2HAL(
    jsonContent,
    verbose=False,
    prod="preprod",
    credentials=None,
    completion=None,
    idhal=None,
):
    """Create a new HAL entry from JSON metadata.
    
    Loads metadata from JSON dict or file, instantiates appropriate HALelt subclass
    based on document type, and uploads to HAL via SWORD protocol.
    
    Args:
        jsonContent (dict or str): Document metadata as dict or path to JSON file.
        verbose (bool): Enable debug logging.
        prod (str): Server mode ('preprod', 'prod', or 'test'). Default: 'preprod'.
        credentials (dict): HAL credentials {'login': '...', 'passwd': '...'}.
            If None, attempts to load from ~/.apihal or environment variables.
        completion (str, optional): Grobid completion options.
        idhal (str, optional): Deposit on behalf of this user.
    
    Returns:
        int: Exit status code (os.EX_OK=0 on success, or EX_* on error).
    
    Example:
        >>> status = runJSON2HAL(
        ...     'metadata.json',
        ...     credentials={'login': 'user', 'passwd': '...'},
        ...     prod='preprod'
        ... )
    """
    exitStatus = os.EX_CONFIG
    # activate verbose mode
    verboseMode(verbose) 

    logger.info("Run JSON2HAL")
    logger.info("")

    # activate production mode
    serverType,testMode = selectServerMode(prod)

    #
    dataJSON, dirPath, new_xml = _load_json_input(jsonContent)
    if dataJSON is None:
        exitStatus = os.EX_OSFILE
        return exitStatus

    document = elt.HALelt.from_input(dataJSON)
    pdf_path = _resolve_document_pdf(document, dirPath=dirPath)
    if dataJSON.get("file", None) and pdf_path is None:
        exitStatus = os.EX_OSFILE
        return exitStatus
    options = _build_upload_options(
        completion=completion,
        idhal=idhal,
        testMode=testMode,
    )
    return document.upload(
        credentials=credentials,
        server=serverType,
        dirPath=dirPath,
        xmlFileName=new_xml,
        pdf_path=pdf_path,
        options=options,
    )
    
def updateHAL(
    data=None,
    pdf_path = None,
    verbose=False,
    prod="preprod",
    credentials=None,
    completion=None,
    halid=None,
    idhal=None
):
    """Update an existing HAL entry with new metadata and/or PDF.
    
    Retrieves existing entry from HAL, merges new metadata, preserves original
    document type, rebuilds TEI XML, and uploads changes back to HAL.
    
    Document Type Preservation: The type from the existing HAL entry is always preserved,
    even if 'type' is specified in the update data. This prevents accidental downgrades.
    
    Args:
        data (dict or str, optional): Metadata updates (dict or path to JSON file).
            Only fields specified will be updated; others preserved.
        pdf_path (str, optional): Path to new PDF file to upload.
        halid (str): HAL ID of entry to update (e.g., 'hal-01234567'). Required.
        verbose (bool): Enable debug logging.
        prod (str): Server mode ('preprod', 'prod', or 'test'). Default: 'preprod'.
        credentials (dict): HAL credentials. If None, attempts to load from ~/.apihal.
        completion (str, optional): Grobid completion options.
        idhal (str, optional): Deposit on behalf of this user.
    
    Returns:
        int: Exit status code (os.EX_OK=0 on success, or EX_* on error).
    
    Example:
        >>> status = updateHAL(
        ...     data={'abstract': {'en': 'Updated abstract'}},
        ...     halid='hal-01234567',
        ...     credentials={'login': 'user', 'passwd': '...'},
        ...     prod='preprod'
        ... )
    """
    exitStatus = os.EX_CONFIG
    
    if data is None:
        data = {}

    if len(data) == 0 or halid is None:
        logger.error("No data or halid provided")
        exitStatus = os.EX_SOFTWARE
        return exitStatus

    # activate verbose mode
    verboseMode(verbose)

    logger.info("Run updateHAL")
    logger.info("")

    # activate production mode
    serverType,testMode = selectServerMode(prod)
    
    if not halid:
        logger.error("No halid provided")
        exitStatus = os.EX_SOFTWARE
        return exitStatus
    
    # get data from HAL
    api = libAPI.APIHAL()
    tei_content = api.search(query={"doc_idhal": halid},
                                 returnFormat="xml-tei")
    if tei_content is None:
        logger.error("No data found for halid: {}".format(halid))
        exitStatus = os.EX_SOFTWARE
        return exitStatus
    else:
        tei_content = tei_content[0]
    
    # update TEI file
    dataJSON, dirPath, new_xml = _load_json_input(data)
    if dataJSON is None:
        exitStatus = os.EX_OSFILE
        return exitStatus

    document = elt.HALelt.fromXMLContent(
        tei_content.getroottree().getroot(),
        data=dataJSON,
    )
    pdf_path = _resolve_document_pdf(document, dirPath=dirPath, pdf_path=pdf_path)
    if (pdf_path is not None or dataJSON.get("file", None)) and pdf_path is None:
        exitStatus = os.EX_OSFILE
        return exitStatus
    options = _build_upload_options(
        completion=completion,
        idhal=idhal,
        testMode=testMode,
    )
    return document.upload(
        credentials=credentials,
        server=serverType,
        dirPath=dirPath,
        xmlFileName=new_xml,
        pdf_path=pdf_path,
        options=options,
        hal_id=halid,
    )


def runPDF2HAL(
    pdf_path,
    verbose=False,
    prod="preprod",
    credentials=None,
    completion=None,
    halid=None,
    idhal=None,
    interaction=True,
):
    """Add a PDF to an existing HAL entry or create new entry with PDF.
    
    Analyzes PDF to extract title, searches HAL for matching entries (if halid not
    provided), retrieves TEI XML, attaches PDF, and uploads back to HAL.
    
    Interactive Mode: If halid not provided and interaction=True, will:
      1. Extract title from PDF
      2. Search HAL for documents with matching title
      3. Display results (numbered list)
      4. Prompt user to select one
    
    Non-Interactive Mode: If halid not provided and interaction=False, will fail with error.
    
    Args:
        pdf_path (str): Path to PDF file to upload. Required.
        halid (str, optional): HAL ID of target entry (e.g., 'hal-01234567').
            If not provided, interactive search will be used (if interaction=True).
        verbose (bool): Enable debug logging.
        prod (str): Server mode ('preprod', 'prod', or 'test'). Default: 'preprod'.
        credentials (dict): HAL credentials. If None, attempts to load from ~/.apihal.
        completion (str, optional): Grobid completion options.
        idhal (str, optional): Deposit on behalf of this user.
        interaction (bool): Enable interactive mode for HAL ID selection. Default: True.
    
    Returns:
        int: Exit status code (os.EX_OK=0 on success, or EX_* on error).
    
    Raises:
        IOError: If PDF file does not exist (converted to EX_OSFILE).
        RequestException: If HAL API unreachable (converted to EX_SOFTWARE).
    
    Example:
        >>> # With known HAL ID
        >>> status = runPDF2HAL(
        ...     'article.pdf',
        ...     halid='hal-01234567',
        ...     credentials={'login': 'user', 'passwd': '...'},
        ...     prod='preprod'
        ... )
        
        >>> # With interactive search
        >>> status = runPDF2HAL(
        ...     'article.pdf',
        ...     credentials={'login': 'user', 'passwd': '...'},
        ...     interaction=True
        ... )
    """
    exitStatus = os.EX_CONFIG
    # activate verbose mode
    verboseMode(verbose)

    logger.info("Run PDF2HAL")
    logger.info("")

    # activate production mode
    serverType,testMode = selectServerMode(prod)

    # check if file exists
    if os.path.isfile(pdf_path):
        logger.debug("PDF file: {}".format(pdf_path))
        dirPath = os.path.dirname(pdf_path)
        logger.debug("Directory: {}".format(dirPath))
        title = m.extract_info(pdf_path)
    else:
        logger.error("PDF file not found")
        exitStatus = os.EX_OSFILE
        return exitStatus

    # show first characters of pdf file
    m.showPDFcontent(pdf_path, number=dflt.DEFAULT_NB_CHAR)

    # check title and/or provide new one
    if not halid:
        if interaction:
            title = m.checkTitle(title)
        else:
            logger.info("Force mode: use title '{}'".format(title))

        # Search for the PDF title in HAL.science
        selected_result = {}
        while not (isinstance(selected_result, dict) and "title_s" in selected_result):
            api = libAPI.APIHAL()
            archives_results = api.search(
                query= {"title": title},
                returnFields=['title_s','halId_s','author_full_name_exact'],
                returnFormat="json")

            if archives_results:
                choice = libAPI.choose_from_results(
                    archives_results, not interaction
                )
                if isinstance(choice, dict):
                    selected_result = choice
                else:
                    selected_result = {}
                    title = choice
            else:
                logger.error("No result found in HAL.science")
                exitStatus = os.EX_SOFTWARE
                return exitStatus

        if isinstance(selected_result, dict) and selected_result:
            selected_title = selected_result.get("title_s", "N/A")
            selected_author = selected_result.get("authFullName_s", "N/A")
            hal_id = selected_result.get("halId_s", None)

            logger.info("Selected result in archives-ouvertes.fr:")
            logger.info("Title: {}".format(selected_title))
            logger.info("Author: {}".format(selected_author))
            logger.info("HAL-id: {}".format(hal_id))
    else:
        logger.info("Provided HAL_id: {}".format(halid))
        hal_id = halid
        # get data from HAL
        # api = libAPI.APIHAL()
        # dataHAL = api.search(query={"halId_s": hal_id}, 
        #                      returnFields=['title_s','halId_s','author_full_name_exact'],
        #                      returnFormat="json")
        objHAL = libAPI.directAccess(hal_id=hal_id, 
                                   type="json")
        dataHAL = objHAL.data
        
        if isinstance(dataHAL, dict) and dataHAL:
            logger.debug("Data from HAL: {}".format(dataHAL))
            selected_title = dataHAL.get("title_s", "N/A")
            selected_author = dataHAL.get("authFullName_s", "N/A")
            hal_id = dataHAL.get("halId_s", None)

            logger.info("Title: {}".format(selected_title))
            logger.info("Author: {}".format(selected_author))
            logger.info("HAL-id: {}".format(hal_id))
        else:
            logger.error("Document's ID {} not found in HAL".format(hal_id))
            exitStatus = os.EX_SOFTWARE
            return exitStatus

    if hal_id:
        # Download TEI file
        api = libAPI.APIHAL()
        tei_content = api.search(query={"doc_idhal": hal_id},
                                 returnFormat="xml-tei")
        # tei_content = lib.getDataFromHAL(
        #     txtsearch=hal_id, typeI="docId", typeDB="article", typeR="xml-tei"
        # )
        
        # objHAL = libAPI.directAccess(hal_id=hal_id, 
        #                                type="xml-tei")
        # tei_content = objHAL.data

        if tei_content:
            # write TEI file
            tei_file_path = os.path.join(dirPath, hal_id + ".tei.xml")
            logger.debug("Write TEI file: {}".format(tei_file_path))
            m.writeXML(tei_content, tei_file_path)

            options = _build_upload_options(
                completion=completion,
                idhal=idhal,
                testMode=testMode,
            )
            document = elt.HALelt.fromXMLContent(tei_content)
            return document.upload(
                credentials=credentials,
                server=serverType,
                dirPath=dirPath,
                pdf_path=pdf_path,
                options=options,
                hal_id=hal_id,
            )
            
        else:
            logger.error("Failed to download TEI file.")
            exitStatus = os.EX_SOFTWARE
            return exitStatus

    else:
        logger.error("No result selected.")
        exitStatus = os.EX_SOFTWARE
        return exitStatus

    return exitStatus


def verboseMode(verbose=False):
    """Configure logger level for verbose or normal output.
    
    Args:
        verbose (bool): If True, set logger to DEBUG; else INFO.
    """
    # Remove old handler and add new one with appropriate level
    logger.remove()
    if verbose:
        logger.add(sys.stderr, level="DEBUG") 
    else:
        logger.add(sys.stderr, level="INFO") 

def selectServerMode(prod="test"):
    """Select HAL server (preprod/prod/test) and corresponding configuration.
    
    Args:
        prod (str): Server mode name ('preprod', 'prod', or 'test'). Default: 'test'.
    
    Returns:
        tuple: (serverType, testMode) where:
            - serverType (str): HAL server hostname
            - testMode (bool): Test mode flag for SWORD headers
    """
    serverType = "preprod"
    testMode = True
    if prod == "prod":
        logger.info("Execution mode: use production server (USE WITH CAUTION))")
        serverType = "prod"
        testMode = False
    elif prod == "test":
        logger.info("Execution mode: use production server (dry-run))")
        serverType = "prod"
        testMode = True
    else:
        logger.info("Dryrun mode: use preprod server")
        testMode = False
    return serverType, testMode