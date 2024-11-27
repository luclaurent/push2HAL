####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************


import os, sys
import json
from loguru import logger

from . import libHAL as lib
from . import libAPIHAL as libAPI
from . import misc as m
from . import default as dflt



def runJSON2HAL(
    jsonContent,
    verbose=False,
    prod="preprod",
    credentials=None,
    completion=None,
    idhal=None,
):
    """execute using arguments"""
    exitStatus = os.EX_CONFIG
    # activate verbose mode
    logger.remove() #remove the old handler. Else, the old one will work along with the new one you've added below'
    if verbose:
        logger.add(sys.stderr, level="DEBUG") 
    else:
        logger.add(sys.stderr, level="INFO") 

    logger.info("Run JSON2HAL")
    logger.info("")

    # activate production mode
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

    #
    json_path = jsonContent
    new_xml = None
    if type(jsonContent) is dict:
        dataJSON = jsonContent
        new_xml = dflt.DEFAULT_UPLOAD_FILE_NAME_XML
    elif os.path.isfile(json_path):
        logger.debug("JSON file: {}".format(json_path))
        dirPath = os.path.dirname(json_path)
        logger.debug("Directory: {}".format(dirPath))
        # open and load json file
        f = open(json_path, "r")
        # Reading from file
        dataJSON = json.loads(f.read())
        new_xml = os.path.basename(json_path).replace(".json", ".xml")
    else:
        logger.error("JSON file not found")
        exitStatus = os.EX_OSFILE
        return exitStatus

    # build XML tree from json
    xmlData = lib.buildXML(dataJSON)

    # add PDF file if provided
    pdf_path = None
    if dataJSON.get("file", None):
        # file directly found
        pdf_path = dataJSON.get("file", None)
        if not os.path.isfile(pdf_path):
            # file not found, search in the same directory
            pdf_path = os.path.join(dirPath, dataJSON["file"])
        #
        if os.path.isfile(pdf_path):
            logger.debug("PDF file: {}".format(pdf_path))
        else:
            logger.error("PDF file not found")
            exitStatus = os.EX_OSFILE
            return exitStatus
    # deal with specific upload options
    options = dict()
    if completion:
        logger.info(
            "Specific completion option(s) will be used: {}".format(completion)
        )
        options["completion"] = completion
    if idhal:
        logger.info("Deposit on behalf of: {}".format(idhal))
        options["idFrom"] = idhal
    if testMode:
        options["testMode"] = "1"
    else:
        options["testMode"] = "0"
    # prepare payload to upload to HAL
    file, payload = lib.preparePayload(
        xmlData,
        pdf_path,
        dirPath,
        xmlFileName=new_xml,
        hal_id=None,
        options=options,
    )

    # upload to HAL
    if credentials:
        id_hal = lib.upload2HAL(file, 
                                payload=payload, 
                                credentials=credentials, 
                                server=serverType)
        return lib.manageError(id_hal)
    else:
        logger.error("No provided credentials")
        exitStatus = os.EX_CONFIG
        return exitStatus


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
    """execute using arguments"""
    exitStatus = os.EX_CONFIG
    # activate verbose mode
    logger.remove() #remove the old handler. Else, the old one will work along with the new one you've added below'
    if verbose:
        logger.add(sys.stderr, level="DEBUG") 
    else:
        logger.add(sys.stderr, level="INFO") 

    logger.info("Run PDF2HAL")
    logger.info("")

    # activate production mode
    serverType = "preprod"
    testMode = False
    if prod == "prod":
        logger.info("Execution mode: use production server (USE WITH CAUTION))")
        serverType = "prod"
    elif prod == "test":
        logger.info("Execution mode: use production server (dry-run))")
        serverType = "prod"
        testMode = True
    else:
        logger.info("Dryrun mode: use preprod server")

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
        selected_result = dict()
        while "title_s" not in selected_result:
            api = libAPI.APIHAL()
            archives_results = api.search(
                query= {"title": title},
                returnFields=['title_s','halId_s','author_full_name_exact'],
                returnFormat="json")

            if archives_results:
                selected_result = libAPI.choose_from_results(
                    archives_results, not interaction
                )
                if "title_s" not in selected_result:
                    title = selected_result
            else:
                logger.error("No result found in HAL.science")
                exitStatus = os.EX_SOFTWARE
                return exitStatus

        if selected_result:
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
        api = libAPI.APIHAL()
        dataHAL = api.search(query={"halId_s": hal_id}, 
                             returnFields=['title_s','halId_s','author_full_name_exact'],
                             returnFormat="json")
        
        if len(dataHAL) > 0:
            logger.debug("Data from HAL: {}".format(dataHAL))
            selected_title = dataHAL[0].get("title_s", "N/A")
            selected_author = dataHAL[0].get("authFullName_s", "N/A")
            hal_id = dataHAL[0].get("halId_s", None)

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
        tei_content = api.search(query={"halId_s": hal_id},
                                 returnFormat="xml-tei")
        # tei_content = lib.getDataFromHAL(
        #     txtsearch=hal_id, typeI="docId", typeDB="article", typeR="xml-tei"
        # )

        if len(tei_content) > 0:
            # write TEI file
            tei_file_path = os.path.join(dirPath, hal_id + ".tei.xml")
            logger.debug("Write TEI file: {}".format(tei_file_path))
            m.writeXML(tei_content, tei_file_path)

            options = dict()
            # deal with specific upload options
            if completion:
                logger.info(
                    "Specific completion option(s) will be used: {}".format(completion)
                )
                options["completion"] = completion
            if idhal:
                logger.info("Deposit on behalf of: {}".format(idhal))
                options["idFrom"] = idhal
            options["testMode"] = False
            if testMode:
                options["testMode"] = True

            # prepare payload to upload to HAL
            file, payload = lib.preparePayload(
                tei_content=tei_content, 
                pdf_path=pdf_path,
                dirPath=dirPath, 
                hal_id=hal_id, 
                options=options
            )

            # upload to HAL
            if credentials:
                retStatus = lib.upload2HAL(file, 
                                           payload, 
                                           hal_id=hal_id,
                                           credentials=credentials, 
                                           server=serverType)
                return lib.manageError(retStatus)
            else:
                logger.error("No provided credentials")
                exitStatus = os.EX_CONFIG
                return exitStatus
            
        else:
            logger.error("Failed to download TEI file.")
            exitStatus = os.EX_SOFTWARE
            return exitStatus

    else:
        logger.error("No result selected.")
        exitStatus = os.EX_SOFTWARE
        return exitStatus

    return exitStatus
