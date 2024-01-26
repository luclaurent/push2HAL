####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of uploadHAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/uploadHAL
####*****************************************************************************************
####*****************************************************************************************


import logging
import os
import shutil
import tempfile
import requests
from requests.auth import HTTPBasicAuth
from lxml import etree

from . import default as dflt
from . import misc as m

Logger = logging.getLogger("pdf2hal")


def getDataFromHAL(
    title=None,
    DOCid=None,
    typeR="json",
    returnFields="title_s,author_s,halId_s,label_s,docid",
):
    """Search for a title in HAL archives"""
    if title:
        Logger.debug("Searching for title: {}".format(title.lower()))
        query = "title_t:{}".format(title.lower())
    elif DOCid:
        Logger.debug("Searching for document's ID: {}".format(DOCid))
        query = "halId_s:{}".format(DOCid)
    #
    Logger.debug("Return format: {}".format(typeR))

    params = {
        "q": query,
        "fl": returnFields,
        "wt": typeR,
        "rows": dflt.DEFAULT_MAX_NUMBER_RESULTS_QUERY,  # Adjust the number of rows based on your preference
    }
    # request and get response
    response = requests.get(dflt.ARCHIVES_API_URL, params=params)

    if response.status_code == 200:
        if typeR == "json":
            data = response.json().get("response", {}).get("docs", [])
        elif typeR == "xml-tei":
            data = response.text
            # declare namespace
            key, value = list(dflt.DEFAULT_NAMESPACE_XML.items())[0]
            etree.register_namespace(key, value)
            return etree.fromstring(data.encode("utf-8"))
        return data
    return []


def choose_from_results(
    results, forceSelection=False, maxNumber=dflt.DEFAULT_MAX_NUMBER_RESULTS
):
    """Select result from a list of results"""
    Logger.info(dflt.TXT_SEP)
    Logger.info("Multiple results found:")
    # lambda show info
    funShow = lambda x, y: "[{}/{}]. {} - {}".format(
        x + 1, len(results), y.get("label_s", "N/A"), result.get("halId_s", "N/A")
    )
    #
    lastposition = 0
    for i, result in enumerate(results):
        # print only the first maxNumber results
        if i < maxNumber:
            Logger.info(funShow(i, result))
            lastposition = i
        else:
            break

    Logger.info(
        "Select a number to view details (0 to skip or p/n for previous/next selection or m for manual definition): "
    )

    choiceOK = False
    while not choiceOK:
        if forceSelection:
            choice = "1"
            choiceOK = True
        else:
            choice = input(" > ")

        if choice.isdigit() and 0 <= int(choice) <= len(results):
            selected_result = results[int(choice) - 1]
            return selected_result
        elif choice == "m":
            Logger.info("Provide title manually")
            manualTitle = input(" > ")
            return manualTitle
        elif choice == "p":
            Logger.info("Previous selection")
            if lastposition - 1 >= 0:
                lastposition -= 1
            else:
                Logger.warning("No previous selection.")
            Logger.info(funShow(lastposition, results[lastposition]))
        elif choice == "n":
            Logger.info("Next selection")
            if lastposition + 1 < len(results):
                lastposition += 1
            else:
                Logger.warning("No next selection.")
            Logger.info(funShow(lastposition, results[lastposition]))
        else:
            Logger.warning("Invalid choice.")

    return None


def addFileInXML(inTree, filePath, hal_id):
    """Add new imported file in XML"""
    newFilename = dflt.DEFAULT_UPLOAD_FILE_NAME_PDF.format(hal_id)
    Logger.debug("Copy original file to new one: {}->{}".format(filePath, newFilename))
    shutil.copyfile(filePath, newFilename)
    # find section to add file
    inS = inTree.find(".//editionStmt", inTree.nsmap)
    if len(inS) == 0:
        newE = etree.Element("editionStmt", nsmap=inTree.nsmap)
        pos = inTree.find(".//titleStmt", inTree.nsmap)
        pos.addnext(newE)
        inS = inTree.find(".//editionStmt", inTree.nsmap)
    # find subsection
    inSu = inS.find(".//edition", inTree.nsmap)
    if len(inSu) == 0:
        inSu = etree.SubElement(inS, "edition", nsmap=inTree.nsmap)

    # check existing file
    # nFile = inS.xpath("//ref[@type='file']") #find('.//ref',inTree.nsmap)
    # add file
    Logger.debug("Add file in XML: {}".format(newFilename))
    nFile = etree.SubElement(inSu, "ref", nsmap=inTree.nsmap)
    nFile.set("type", "file")
    nFile.set("subtype", "author")
    nFile.set("n", "1")
    nFile.set("target", newFilename)
    return newFilename


def buildZIP(xml_file_path, pdf_file_path):
    """Build ZIP archive for HAL deposit (containing XML and PDF)"""
    # create temporary directory
    tmp_dir_path = tempfile.mkdtemp()
    Logger.debug("Create temporary directory: {}".format(tmp_dir_path))
    Logger.debug("Copy XML file: {}->{}".format(xml_file_path, tmp_dir_path))
    shutil.copy(xml_file_path, tmp_dir_path)
    Logger.debug("Copy PDF file: {}->{}".format(pdf_file_path, tmp_dir_path))
    shutil.copy(pdf_file_path, tmp_dir_path)
    # build zip archive
    archivePath = dflt.DEFAULT_UPLOAD_FILE_NAME_ZIP
    Logger.debug("Create zip archive: {}".format(archivePath + "zip"))
    shutil.make_archive(archivePath, "zip", tmp_dir_path)
    return archivePath + ".zip"


def preparePayload(
    tei_content, pdf_path=None, dirPath=None, hal_id=None, options=dict()
):
    """Prepare payload for HAL deposit"""
    # clean XML
    if pdf_path:
        m.cleanXML(tei_content, ".//idno[@type='stamp']")
        # declare new file as target in xml
        newPDF = addFileInXML(tei_content, pdf_path, hal_id)
    # write xml file
    xml_file_path = os.path.join(dirPath, dflt.DEFAULT_UPLOAD_FILE_NAME_XML)
    m.writeXML(tei_content, xml_file_path)
    # build zip file
    if pdf_path:
        zipfile = buildZIP(xml_file_path, newPDF)
    # create header
    header = dict()
    # default:
    header["Content-Disposition"] = m.adaptH(None)
    # header['On-Behalf-Of'] = m.adaptH(options.get('idFrom',None))
    header["Export-To-Arxiv"] = m.adaptH(False)
    header["Export-To-PMC"] = m.adaptH(False)
    header["Hide-For-RePEc"] = m.adaptH(False)
    header["Hide-In-OAI"] = m.adaptH(False)
    header["X-Allow-Completion"] = m.adaptH(options.get("allowCompletion", False))
    header["Packaging"] = m.adaptH(
        options.get("allowCompletion", dflt.DEFAULT_XML_SWORD_PACKAGING)
    )
    if pdf_path:
        header["Content-Type"] = m.adaptH("application/zip")
        header["Export-To-Arxiv"] = m.adaptH(
            options.get("export2arxiv", header["Export-To-Arxiv"])
        )
        header["Export-To-PMC"] = m.adaptH(
            options.get("export2pmc", header["Export-To-PMC"])
        )
        header["Hide-For-RePEc"] = m.adaptH(
            options.get("hide4repec", header["Hide-For-RePEc"])
        )
        header["Hide-In-OAI"] = m.adaptH(options.get("hide4oai", header["Hide-In-OAI"]))
        header["Content-Disposition"] = m.adaptH(
            'attachment; filename="{}"'.format(xml_file_path)
        )
    else:
        header["Content-Type"] = m.adaptH("text/xml")

    return zipfile, header


def upload2HAL(file, headers, credentials, server="preprod"):
    """Upload to HAL"""
    Logger.info("Upload to HAL")
    Logger.debug("File: {}".format(file))
    Logger.debug("Headers: {}".format(headers))

    if server == "preprod":
        url = dflt.ARCHIVES_SWORD_PRE_API_URL
    else:
        url = dflt.ARCHIVES_SWORD_API_URL

    Logger.debug("Upload via {}".format(url))
    # read data to sent
    with open(file, "rb") as f:
        data = f.read()

    res = requests.post(
        url=url,
        data=data,
        headers=headers,
        auth=HTTPBasicAuth(credentials["login"], credentials["passwd"]),
    )

    if res.status_code == 201:
        Logger.info("Successfully upload to HAL.")
    else:
        # read error message
        xmlResponse = etree.fromstring(res.text.encode("utf-8"))
        elem = xmlResponse.findall(
            dflt.DEFAULT_ERROR_DESCRIPTION_SWORD_LOC, xmlResponse.nsmap
        )
        Logger.error("Failed to upload. Status code: {}".format(res.status_code))
        if len(elem) > 0:
            for i in elem:
                Logger.warning("Error: {}".format(i.text))
