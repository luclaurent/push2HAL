####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************


from loguru import logger
import os,sys
import shutil
import tempfile
import requests
import difflib
import json
from requests.auth import HTTPBasicAuth
from lxml import etree
import re
from unidecode import unidecode
from stdnum import isbn, issn

from . import default as dflt
from . import misc as m

## create a custom logger
logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> |"
    "<red>PUSH2HAL</red> |"
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra[ip]} {extra[user]} - <level>{message}</level>"
)

logger.remove()
logger.add(sys.stderr, format=logger_format)


## get XML's namespace for everything
TEI = "{%s}" % dflt.DEFAULT_TEI_URL_NAMESPACE


def getDataFromHAL(
    txtsearch=None,
    typeI=None,
    typeDB="article",
    typeR="json",
    returnFields="title_s,author_s,halId_s,label_s,docid",
    url=dflt.HAL_API_SEARCH_URL,
):
    """
    Search for data in HAL archives based on the specified parameters.

    Args:
        txtsearch (str, optional): The search text. Defaults to None.
        typeI (str, optional): The type of search. Defaults to None.
        typeDB (str, optional): The type of database to search in. Defaults to "article".
        typeR (str, optional): The return format of the search results. Defaults to "json".
        returnFields (str, optional): The fields to include in the search results. Defaults to "title_s,author_s,halId_s,label_s,docid".
        url (str, optional): The URL of the HAL API. Defaults to dflt.HAL_API_SEARCH_URL.

    Returns:
        list or dict or str: The search results based on the specified return format.

    """
    if typeDB:
        logger.debug("Searching in database: {}".format(typeDB))
        if typeDB == "journal":
            url = dflt.HAL_API_JOURNAL_URL
        elif typeDB == "article":
            url = dflt.HAL_API_SEARCH_URL
        elif typeDB == "anrproject":
            url = dflt.HAL_API_ANR_URL
        elif typeDB == "authorstruct":
            url = dflt.HAL_API_AUTHORSTRUCT_URL
        elif typeDB == "europeanproject":
            url = dflt.HAL_API_EUROPPROJ_URL
        elif typeDB == "doc":
            url = dflt.HAL_API_DOC_URL
        elif typeDB == "domain":
            url = dflt.HAL_API_DOMAIN_URL
        elif typeDB == "instance":
            url = dflt.HAL_API_INSTANCE_URL
        elif typeDB == "metadata":
            url = dflt.HAL_API_METADATA_URL
        elif typeDB == "metadatalist":
            url = dflt.HAL_API_METADATALIST_URL
        elif typeDB == "structure":
            url = dflt.HAL_API_STRUCTURE_URL
        else:
            logger.warning("Unknown database: {}".format(typeDB))

    if typeI == "title":
        logger.debug("Searching for title: {}".format(txtsearch.lower()))
        query = "title_t:{}".format(txtsearch.lower())
    elif typeI == "title_approx":
        logger.debug("Searching for approximated title: {}".format(txtsearch.lower()))
        query = "title_s:{}".format(txtsearch.lower())
    elif typeI == "docId":
        logger.debug("Searching for document's ID: {}".format(txtsearch))
        query = "halId_s:{}".format(txtsearch)
    elif typeI == "doi":
        logger.debug("Searching for document's doi: {}".format(txtsearch))
        query = "doiId_id:{}".format(txtsearch)
    #
    logger.debug("Return format: {}".format(typeR))

    params = {
        "q": query,
        "fl": returnFields,
        "wt": typeR,
        "rows": dflt.DEFAULT_MAX_NUMBER_RESULTS_QUERY,  # Adjust the number of rows based on your preference
    }
    # request and get response
    response = requests.get(url, params=params)

    if response.status_code == 200:
        if typeR == "json":
            data = response.json().get("response", {}).get("docs", [])
        elif typeR == "xml-tei":
            data = response.text
            # declare namespace
            # key, value = list(dflt.DEFAULT_NAMESPACE_XML.items())[0]
            # etree.register_namespace(key, value)
            return etree.fromstring(data.encode("utf-8"))
        return data
    return []

def checkDoiInHAL(doi, returnID=True):
    """ Check if DOI is already in HAL.

    Args:
        doi (str): The DOI to check.

    Returns:
        bool: True if the DOI is already in HAL, False otherwise.
    """
    # request
    dataFromHAL = getDataFromHAL(txtsearch=doi,
                                    typeI='doi',
                                    typeDB="article",
                                    typeR="json")
    return_code = False
    if dataFromHAL:
        if len(dataFromHAL) > 0:
            return_code = True
    return return_code


def choose_from_results(
    results, forceSelection=False, maxNumber=dflt.DEFAULT_MAX_NUMBER_RESULTS
):
    """
    Interactive selection of a result from a list of results.

    Args:
        results (list): A list of results to choose from.
        forceSelection (bool, optional): If True, a result will be automatically selected. Defaults to False.
        maxNumber (int, optional): The maximum number of results to display. Defaults to the default maximum number.

    Returns:
        selected_result: The selected result from the list, or a manually provided title.

    """
    logger.info(dflt.TXT_SEP)
    logger.info("Multiple results found:")
    # lambda show info
    funShow = lambda x, y: "[{}/{}]. {} - {}".format(
        x + 1, len(results), y.get("label_s", "N/A"), result.get("halId_s", "N/A")
    )
    #
    lastposition = 0
    for i, result in enumerate(results):
        # print only the first maxNumber results
        if i < maxNumber:
            logger.info(funShow(i, result))
            lastposition = i
        else:
            break

    logger.info(
        "Select a number to view details (0 to skip or p/n for previous/next selection or m for manual definition): "
    )

    choiceOK = False
    while not choiceOK:
        # if selection is forced: first result used
        if forceSelection:
            choice = "1"
            choiceOK = True
        else:
            choice = input(" > ")
        # depending on the input
        if choice.isdigit() and 0 <= int(choice) <= len(results):
            selected_result = results[int(choice) - 1]
            return selected_result
        elif choice == "m":
            logger.info("Provide title manually")
            manualTitle = input(" > ")
            return manualTitle
        elif choice == "p":
            logger.info("Previous selection")
            if lastposition - 1 >= 0:
                lastposition -= 1
            else:
                logger.warning("No previous selection.")
            logger.info(funShow(lastposition, results[lastposition]))
        elif choice == "n":
            logger.info("Next selection")
            if lastposition + 1 < len(results):
                lastposition += 1
            else:
                logger.warning("No next selection.")
            logger.info(funShow(lastposition, results[lastposition]))
        else:
            logger.warning("Invalid choice.")

    return None


def manageError(e):
    """ Manage return code from upload2HAL """
    if e == 201:
        # logger.info("Successfully upload to HAL.")
        pass
    elif e == 202:
        # logger.info("Note accepted by HAL.")
        pass
    elif e == 401:
        # logger.info("Authentification refused - check credentials")
        e = os.EX_SOFTWARE
    elif e == 400:
        # logger.info("Internal error - check XML file")
        e = os.EX_SOFTWARE
    return e


