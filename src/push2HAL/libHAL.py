####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************


import logging
import os
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

Logger = logging.getLogger("push2HAL")


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
    """Search for a title in HAL archives"""
    if typeDB:
        Logger.debug("Searching in database: {}".format(typeDB))
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
            Logger.warning("Unknown database: {}".format(typeDB))

    if typeI == "title":
        Logger.debug("Searching for title: {}".format(txtsearch.lower()))
        query = "title_t:{}".format(txtsearch.lower())
    elif typeI == "title_approx":
        Logger.debug("Searching for approximated title: {}".format(txtsearch.lower()))
        query = "title_s:{}".format(txtsearch.lower())
    elif typeI == "docId":
        Logger.debug("Searching for document's ID: {}".format(txtsearch))
        query = "halId_s:{}".format(txtsearch)
    elif typeI == "doi":
        Logger.debug("Searching for document's doi: {}".format(txtsearch))
        query = "doiId_id:{}".format(txtsearch)
    #
    Logger.debug("Return format: {}".format(typeR))

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

def checkDoiInHAL(doi):
    """ Check if DOI is already in HAL """
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


def addFileInXML(inTree, filePath, hal_id="upload"):
    """Add new imported file in XML"""
    newFilename = dflt.DEFAULT_UPLOAD_FILE_NAME_PDF.format(hal_id)
    Logger.debug("Copy original file to new one: {} -> {}".format(filePath, newFilename))
    shutil.copyfile(filePath, newFilename)
    # find section to add file
    inS = inTree.find(".//editionStmt", inTree.nsmap)
    if inS is None:
        newE = etree.SubElement(inTree, TEI + "editionStmt")  # , nsmap=inTree.nsmap)
        pos = inTree.find(".//titleStmt", inTree.nsmap)
        pos.addnext(newE)
        inS = inTree.find(".//editionStmt", inTree.nsmap)
    # find subsection
    inSu = inS.find(".//edition", inTree.nsmap)
    if inSu is None:
        inSu = etree.SubElement(inS, TEI + "edition") #, nsmap=inTree.nsmap)

    # check existing file
    # nFile = inS.xpath("//ref[@type='file']") #find('.//ref',inTree.nsmap)
    # add file
    Logger.debug("Add file in XML: {}".format(newFilename))
    nFile = etree.SubElement(inSu, TEI + "ref", nsmap=inTree.nsmap)
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
    xml_file_dst = os.path.join(tmp_dir_path, dflt.DEFAULT_UPLOAD_FILE_NAME_XML)
    Logger.debug("Copy XML file: {} -> {}".format(xml_file_path, xml_file_dst))
    shutil.copy(xml_file_path, xml_file_dst)
    Logger.debug("Copy PDF file: {} -> {}".format(pdf_file_path, tmp_dir_path))
    shutil.copy(pdf_file_path, tmp_dir_path)
    # build zip archive
    archivePath = dflt.DEFAULT_UPLOAD_FILE_NAME_ZIP
    Logger.debug("Create zip archive: {}".format(archivePath + ".zip"))
    shutil.make_archive(archivePath, "zip", tmp_dir_path)
    return archivePath + ".zip"


def preparePayload(
    tei_content,
    pdf_path=None,
    dirPath=None,
    xmlFileName=dflt.DEFAULT_UPLOAD_FILE_NAME_XML,
    hal_id=None,
    options=dict(),
):
    """Prepare payload for HAL deposit"""
    # clean XML
    if pdf_path:
        m.cleanXML(tei_content, ".//idno[@type='stamp']")
        # declare new file as target in xml
        newPDF = addFileInXML(tei_content, pdf_path, hal_id)
    # write xml file
    xml_file_path = os.path.join(dirPath, xmlFileName)
    m.writeXML(tei_content, xml_file_path)
    sendfile = xml_file_path
    # build zip file
    if pdf_path:
        sendfile = buildZIP(xml_file_path, newPDF)

    # create header
    header = dict()
    # default:
    header["Content-Disposition"] = m.adaptH(dflt.DEFAULT_CONTENT_DISPOSITION)
    if options.get("idFrom", None):
        header["On-Behalf-Of"] = m.adaptH(options.get("idFrom", None))
    header["Export-To-Arxiv"] = m.adaptH(dflt.DEFAULT_EXPORT_ARCHIVE)
    header["Export-To-PMC"] = m.adaptH(dflt.DEFAULT_EXPORT_PMC)
    header["Hide-For-RePEc"] = m.adaptH(dflt.DEFAULT_HIDE_REPEC)
    header["Hide-In-OAI"] = m.adaptH(dflt.DEFAULT_HIDE_OAI)
    header["X-Allow-Completion"] = m.adaptH(
        options.get("completion", dflt.DEFAULT_ALLOW_COMPLETION)
    )
    header["Packaging"] = m.adaptH(dflt.DEFAULT_XML_SWORD_PACKAGING)
    header["X-test"] = m.adaptH(options.get("testMode", dflt.DEFAULT_HAL_TEST))
    if header["X-test"] == "1":
        Logger.warning("Test mode activated")
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
            "attachment; filename={}".format(xmlFileName)   # path inside the archive
        )
    else:
        header["Content-Type"] = m.adaptH("text/xml")

    return sendfile, header


def upload2HAL(file, headers, credentials, server="preprod"):
    """Upload to HAL"""
    Logger.info("Upload to HAL")
    Logger.debug("File: {}".format(file))
    Logger.debug("Headers: {}".format(headers))

    if server == "preprod":
        url = dflt.HAL_SWORD_PRE_API_URL
    else:
        url = dflt.HAL_SWORD_API_URL

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
    
     
    hal_id = None
    if res.status_code == 201:
        Logger.info("Successfully upload to HAL.")
    elif res.status_code == 202:
        Logger.info("Note accepted by HAL.")
        # read return message
        xmlResponse = etree.fromstring(res.text.encode("utf-8"))
        elem = xmlResponse.findall("id", xmlResponse.nsmap)
        hal_id = elem[0].text
        Logger.debug("HAL ID: {}".format(elem[0].text))
    elif res.status_code == 401:
        Logger.info("Authentification refused - check credentials")
    else:
        # read error message
        xmlResponse = etree.fromstring(res.text.encode("utf-8"))
        elem = xmlResponse.findall(
            dflt.DEFAULT_ERROR_DESCRIPTION_SWORD_LOC, xmlResponse.nsmap
        )
        Logger.error("Failed to upload. Status code: {}".format(res.status_code))
        if len(elem) > 0:
            json_ret = list()
            for i in elem:
                content = None
                try:
                    content = json.loads(i.text)
                except:
                    pass
                if content is None:
                    content = i.text
                json_ret.append(content)
                Logger.warning("Error: {}".format(i.text))
        # extract hal_id
        for j in json_ret:
            if type(j) is dict:
                if j.get('duplicate-entry'):
                    hal_id = list(j.get('duplicate-entry').keys())[0]
    return hal_id

def setTitles(nInTree, titles, subTitles=None):
    """Add title(s) and subtitle(s) in XML (and specified language)"""
    if subTitles:
        listTitles = {"titles": titles, "subtitles": subTitles}
    else:
        listTitles = {"titles": titles}
    nTitle = list()
    for k, n in listTitles.items():
        if type(n) == dict:
            for l, t in n.items():
                nTitle.append(etree.SubElement(nInTree, TEI + "title"))
                if k == "subtitles":
                    nTitle[-1].set("type", "sub")
                nTitle[-1].set(dflt.DEFAULT_XML_LANG + "lang", l)
                nTitle[-1].text = t
        else:
            Logger.warning("No language for title: force english")
            nTitle.append(etree.SubElement(nInTree, TEI + "title"))
            if k == "subtitles":
                nTitle[-1].set("type", "sub")
            nTitle[-1].set(dflt.DEFAULT_XML_LANG + "lang", "en")
            nTitle[-1].text = n
    return nTitle


def getNameFormated(a):
    """format name from dict to list"""
    l = [a["firstname"]]
    l.append(a.get("middle", None))
    l.append(a["lastname"])
    l = list(filter(None, l))
    return l


def setAuthors(inTree, authors):
    """Add authors in XML (and linked to affiliation)"""
    nAuthors = list()
    for a in authors:
        # format name
        nameFormated = getNameFormated(a)
        nAuthors.append(etree.SubElement(inTree, TEI + "author"))
        # roles: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:relator&fl=*&wt=xml
        if "role" in a:
            nAuthors[-1].set("role", a["role"])
        else:
            Logger.warning(
                "No role for author {} {}: force aut".format(
                    nameFormated[0], nameFormated[-1]
                )
            )
            nAuthors[-1].set("role", "aut")
        persName = etree.SubElement(nAuthors[-1], TEI + "persName")
        forename = etree.SubElement(persName, TEI + "forename")
        forename.set("type", "first")
        forename.text = nameFormated[0]
        if len(nameFormated) > 2:
            forename = etree.SubElement(persName, TEI + "forename")
            forename.set("type", "middle")
            forename.text = nameFormated[1]
        surname = etree.SubElement(persName, TEI + "surname")
        surname.text = nameFormated[-1]
        if a.get("email", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "email")
            idA.text = a["email"]
        if a.get("idhal", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "idno")
            idA.set("type", "idhal")
            idA.text = a["idhal"]
        if a.get("halauthor", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "idno")
            idA.set("type", "halauthor")
            idA.text = a["halauthor"]
        if a.get("url", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "ptr")
            idA.set("type", "url")
            idA.set("target", a["url"])
        if a.get("orcid", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "idno")
            idA.set("type", dflt.ID_ORCID_URL)
            idA.text = a["orcid"]
        if a.get("arxiv", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "idno")
            idA.set("type", dflt.ID_ARXIV_URL)
            idA.text = a["arxiv"]
        if a.get("researcherid", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "idno")
            idA.set("type", dflt.ID_RESEARCHERID_URL)
            idA.text = a["researcherid"]
        if a.get("idref", None):
            idA = etree.SubElement(nAuthors[-1], TEI + "idno")
            idA.set("type", dflt.ID_IDREF_URL)
            idA.text = a["idref"]
        if a.get("affiliation", None):
            if type(a["affiliation"]) is not list:
                list_aff = [a["affiliation"]]
            else:
                list_aff = a["affiliation"]
            for aff in list_aff:
                nAff = etree.SubElement(nAuthors[-1], TEI + "affiliation")
                nAff.set("ref", "#localStruct-" + aff)
        if a.get("affiliationHAL", None):
            if type(a["affiliationHAL"]) is not list:
                list_aff = [a["affiliationHAL"]]
            else:
                list_aff = a["affiliationHAL"]
            for aff in list_aff:
                nAff = etree.SubElement(nAuthors[-1], TEI + "affiliation")
                idStrut = aff
                idStruct = re.sub("^#struct-", "", idStrut)
                nAff.set("ref", "#struct-" + idStruct)
    return nAuthors


def setLicence(inTree, licence):
    """Set licence in XML"""
    availability = etree.SubElement(inTree, TEI + "availability")
    lic_cc = etree.SubElement(availability, TEI + "licence")
    # all licences: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:licence&fl=*&wt=xml
    if type(licence) is dict:
        licenceV = licence["licence"]
    else:
        licenceV = licence
    Logger.warning("licence: {} (works only for Creative Commons one)".format(licenceV))
    lic_cc.set("target", dflt.ID_CC_URL + "/" + licenceV + "/")


def setStamps(inTree, stamps):
    """Set stamps in XML (probably not accepted by HAL)"""
    nStamps = list()
    if type(stamps) is not list:
        list_stamps = [stamps]
    else:
        list_stamps = stamps
    for s in list_stamps:
        nStamps.append(etree.SubElement(inTree, TEI + "idno"))
        nStamps[-1].set("type", "stamp")
        nStamps[-1].set("n", s["name"])
    return nStamps


def getAudience(notes):
    # see all audience codes: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:audience&fl=*&wt=xml
    # default audience
    audienceFlag = notes.get("audience", dflt.DEFAULT_AUDIENCE)
    if str(audienceFlag).lower().startswith("international"):
        audienceFlag = "2"
    elif str(audienceFlag).lower().startswith("national"):
        audienceFlag = "3"
    if (
        str(audienceFlag) != "1"
        and str(audienceFlag) != "2"
        and str(audienceFlag) != "3"
    ):
        Logger.warning(
            "Unknown audience: force default ({})".format(dflt.DEFAULT_AUDIENCE)
        )
        audienceFlag = dflt.DEFAULT_AUDIENCE
    return audienceFlag


def getInvited(notes):
    # see all invited codes: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:invitedCommunication&fl=*&wt=xml
    # default invited
    invitedFlag = notes.get("invited", dflt.DEFAULT_INVITED)
    if str(invitedFlag).lower().startswith(("o", "y", "1", "t")):
        invitedFlag = "1"
    elif str(invitedFlag).lower().startswith(("n", "0", "f")):
        invitedFlag = "0"
    if str(invitedFlag) != "0" and str(invitedFlag) != "1":
        Logger.warning(
            "Unknown invited: force default ({})".format(dflt.DEFAULT_INVITED)
        )
        invitedFlag = dflt.DEFAULT_INVITED
    return invitedFlag


def getPopular(notes):
    # see all popular levels codes: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:popularLevel&fl=*&wt=xml
    # default popular level
    popFlag = notes.get("popular", dflt.DEFAULT_POPULAR)
    if str(popFlag).lower().startswith(("o", "y", "1", "t")):
        popFlag = "1"
    elif str(popFlag).lower().startswith(("n", "0", "f")):
        popFlag = "0"
    if str(popFlag) != "0" and str(popFlag) != "1":
        Logger.warning(
            "Unknown popular level: force default ({})".format(dflt.DEFAULT_POPULAR)
        )
        popFlag = dflt.DEFAULT_POPULAR
    return popFlag


def getPeer(notes):
    # see all peer reviewing codes: hhttps://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:popularLevel&fl=*&wt=xml
    # default peer reviewing
    peerFlag = notes.get("peer", dflt.DEFAULT_PEER)
    if str(peerFlag).lower().startswith(("o", "y", "1", "t")):
        peerFlag = "1"
    elif str(peerFlag).lower().startswith(("n", "0", "f")):
        peerFlag = "0"
    if str(peerFlag) != "0" and str(peerFlag) != "1":
        Logger.warning(
            "Unknown peer reviewing type: force default ({})".format(dflt.DEFAULT_PEER)
        )
        peerFlag = dflt.DEFAULT_PEER
    return peerFlag


def getProceedings(notes):
    # see all peer reviewing codes: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:proceedings&fl=*&wt=xml
    # default proceedings
    proFlag = notes.get("proceedings", dflt.DEFAULT_PROCEEDINGS)
    if str(proFlag).lower().startswith(("o", "y", "1", "t")):
        proFlag = "1"
    elif str(proFlag).lower().startswith(("n", "0", "f")):
        proFlag = "0"
    if str(proFlag) != "0" and str(proFlag) != "1":
        Logger.warning(
            "Unknown proceedings status: force default ({})".format(
                dflt.DEFAULT_PROCEEDINGS
            )
        )
        proFlag = dflt.DEFAULT_PROCEEDINGS
    return proFlag


def setNotes(inTree, notes):
    """Set notes in XML
    NOTE: additionnal notes are supported by HAL but not included here

    INCLUDED:
        <note type="commentary"><!-- %%comment - -> </note>
        <note type="description"><!-- %%description - -> </note>
        <note type="audience" n="2"/><!-- %%audience : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:audience&fl=*&wt=xml - -> 
        <note type="invited" n="1"/><!-- %%invitedCommunication : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:invitedCommunication&fl=*&wt=xml - -> 
        <note type="popular" n="0"/><!-- %%popularLevel : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:popularLevel&fl=*&wt=xml - -> 
        <note type="peer" n="0"/><!-- %%peerReviewing : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:peerReviewing&fl=*&wt=xml - -> 
        <note type="proceedings" n="1"/><!-- %%proceedings : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:proceedings&fl=*&wt=xml - -> 

    NOT INCLUDED:
        <note type="report" n="6"/><!-- %%reportType : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:reportType&fl=*&wt=xml - -> 
        <note type="other" n="crOuv"/><!-- %%otherType : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:otherType&fl=*&wt=xml - -> 
        <note type="image" n="3"/><!-- %%imageType : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:imageType&fl=*&wt=xml - -> 
        <note type="lecture" n="13"/><!-- %%lectureType : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:lectureType&fl=*&wt=xml - -> 
        <note type="pastel_thematique" n="3"/><!-- %%pastel_thematique : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:pastel_thematique&fl=*&wt=xml - -> 
        <note type="pastel_library" n="7"/><!-- %%pastel_library : http://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:pastel_library&fl=*&wt=xml - -> 

    """
    nNotes = list()
    # add element for notes
    idN = etree.SubElement(inTree, TEI + "notesStmt")
    # define audience
    nNotes.append(etree.SubElement(idN, TEI + "note"))
    nNotes[-1].set("type", "audience")
    nNotes[-1].set("n", getAudience(notes))
    # define invited
    nNotes.append(etree.SubElement(idN, TEI + "note"))
    nNotes[-1].set("type", "invited")
    nNotes[-1].set("n", getInvited(notes))
    # define popular
    nNotes.append(etree.SubElement(idN, TEI + "note"))
    nNotes[-1].set("type", "popular")
    nNotes[-1].set("n", getPopular(notes))
    # define peer
    nNotes.append(etree.SubElement(idN, TEI + "note"))
    nNotes[-1].set("type", "peer")
    nNotes[-1].set("n", getPeer(notes))
    # define proceedings
    nNotes.append(etree.SubElement(idN, TEI + "note"))
    nNotes[-1].set("type", "proceedings")
    nNotes[-1].set("n", getProceedings(notes))

    if notes.get("comment", None):
        nNotes.append(etree.SubElement(idN, TEI + "note"))
        nNotes[-1].set("type", "commentary")
        nNotes[-1].text = notes.get("comment")
    if notes.get("description", None):
        nNotes.append(etree.SubElement(idN, TEI + "note"))
        nNotes[-1].set("type", "description")
        nNotes[-1].text = notes.get("description")

    return nNotes


def setAbstract(inTree, abstracts):
    """Add abstract in XML (and specified language)"""
    if abstracts is None:
        Logger.warning("No provided abstract")
        return None
    nAbstract = list()
    if type(abstracts) == str():
        Logger.warning("No language for abstract: force english")
        nAbstract.append(etree.SubElement(inTree, TEI + "abstract"))
        nAbstract[-1].set(dflt.DEFAULT_XML_LANG + "lang", "en")
        nAbstract[-1].text = abstracts
    else:
        nKeywords = list()
        for lk, vk in abstracts.items():
            nAbstract.append(etree.SubElement(inTree, TEI + "abstract"))
            nAbstract[-1].set(dflt.DEFAULT_XML_LANG + "lang", lk)
            nAbstract[-1].text = vk
    return nAbstract
    
    return nAbstract


def setID(inTree, ids, typeId):
    """Add ID of document using idno"""
    idT = None
    if ids:
        idT = etree.SubElement(inTree, TEI + "idno")
        idT.set("type", typeId)
        idT.text = ids
    return idT


def setIDS(inTree, data):
    """Set all IDs"""
    lID = []
    if data.get("nnt", None):
        lID.append(setID(inTree, data.get("nnt"), "nnt"))
    if data.get("isbn", None):
        if not isbn.is_valid(data.get("isbn")):
            Logger.warning("ISBN not valid: {}, continue...".format(data.get("isbn")))
        lID.append(setID(inTree, data.get("isbn"), "isbn"))
    if data.get("patentNumber", None):
        lID.append(setID(inTree, data.get("patentNumber"), "patentNumber"))
    if data.get("reportNumber", None):
        lID.append(setID(inTree, data.get("reportNumber"), "reportNumber"))
    if data.get("localRef", None):
        lID.append(setID(inTree, data.get("localRef"), "localRef"))
    if data.get("halJournalId", None) or not data.get("journal", None) == "none":
        lID.append(setID(inTree, data.get("halJournalId"), "halJournalId"))
    if data.get("journal", None):
        lID.append(setID(inTree, data.get("j"), "j"))
        if data.get("halJournalId", None) is None:
            idJ = getDataFromHAL(
                txtsearch=data.get("journal"),
                typeDB="journal",
                typeI="title",
                returnFields="docid,title_s",
            )
            if idJ is None:
                idJ = getDataFromHAL(
                    textsearch=data.get("journal"),
                    typeDB="journal",
                    typeI="title_approx",
                    returnFields="docid,title_s",
                )
            # adapt id if many are found
            idJournal = None
            if len(idJ) > 1:
                Logger.debug("Identify write journal ID in HAL")
                listJ = [j["title_s"] for j in idJ]
                jName = difflib.get_close_matches(data.get("journal"), listJ)
                ixJ = listJ.index(jName[0])
                idJournal = idJ[ixJ]["docid"]
            if idJournal:
                Logger.debug("Jounal ID found: {}".format(idJournal))
                lID.append(setID(inTree, idJournal, "halJournalId"))
    if data.get("issn", None):
        if not issn.is_valid(data.get("issn")):
            Logger.warning("ISSN not valid: {}, continue...".format(data.get("issn")))
    lID.append(setID(inTree, data.get("issn"), "issn"))
    if data.get("eissn", None):
        if not issn.validate(data.get("eissn")):
            Logger.warning("eISSN not valid: {}, continue...".format(data.get("eissn")))
    lID.append(setID(inTree, data.get("eissn"), "eissn"))
    if data.get("j", None):
        lID.append(inTree.SubElement(inTree, TEI + "title"))
        lID[-1].set("level", "j")
        lID[-1].text = data.get("j")
    if data.get("m", None):
        lID.append(inTree.SubElement(inTree, TEI + "title"))
        lID[-1].set("level", "m")
        lID[-1].text = data.get("m")
    if data.get("booktitle", None):
        lID.append(inTree.SubElement(inTree, TEI + "title"))
        lID[-1].set("level", "m")
        lID[-1].text = data.get("booktitle")
    if data.get("source", None):
        lID.append(inTree.SubElement(inTree, TEI + "title"))
        lID[-1].set("level", "m")
        lID[-1].text = data.get("source")
    return lID


def setConference(inTree, data):
    """Set a conference in XML"""
    idM = etree.SubElement(inTree, TEI + "meeting")
    if data.get("title"):
        idT = etree.SubElement(idM, TEI + "title")
        idT.text = data.get("title")
    if data.get("start"):
        idT = etree.SubElement(idM, TEI + "date")
        idT.set("type", "start")
        idT.text = data.get("start")
    if data.get("end"):
        idT = etree.SubElement(idM, TEI + "date")
        idT.set("type", "end")
        idT.text = data.get("end")
    if data.get("location"):
        idT = etree.SubElement(idM, TEI + "settlement")
        idT.text = data.get("location")
    if data.get("country"):
        idT = etree.SubElement(idM, TEI + "country")
        idT.set("key", m.getAlpha2Country(data.get("country")))
        idT.text = data.get("location")
    if data.get("organizer"):
        idM = etree.SubElement(inTree, TEI + "respStmt")
        idT = etree.SubElement(idM, TEI + "resp")
        idT.text = "conferenceOrganizer"
        #
        dataORG = data.get("organizer")
        if type(dataORG) != list:
            dataORG = [dataORG]
            for d in dataORG:
                idT = etree.SubElement(idM, TEI + "name")
                idT.text = d

    return []


def setLanguage(inTree, language):
    """Set main language in XML"""
    langUsage = etree.SubElement(inTree, TEI + "langUsage")
    if language is None:
        Logger.warning("No language provided - force {}".format(dflt.DEFAULT_LANG_DOC))
        language = dflt.DEFAULT_LANG_DOC
    idL = etree.SubElement(langUsage, TEI + "language")
    idL.set("ident", language)


def setKeywords(inTree, keywords):
    """Set keywords in XML (and specified language)"""
    if keywords is None:
        Logger.warning("No keywords provided")
        return None
    #
    if type(keywords) == str:
        keywords = [keywords]
    itK = etree.SubElement(inTree, TEI + "keywords")
    itK.set("scheme", "author")
    if type(keywords) == list():
        Logger.warning("No language for keywords: force english")
        nKeywords = list()
        for k in keywords:
            nKeywords.append(etree.SubElement(inTree, TEI + "keyword"))
            nKeywords[-1].set(dflt.DEFAULT_XML_LANG + "lang", "en")
            nKeywords[-1].text = k
    else:
        nKeywords = list()
        for lk, vk in keywords.items():
            if type(vk) != list:
                vk = [vk]
            for i in vk:
                nKeywords.append(etree.SubElement(itK, TEI + "term"))
                nKeywords[-1].set(dflt.DEFAULT_XML_LANG + "lang", lk)
                nKeywords[-1].text = i
    return nKeywords


def setCodes(inTree, data):
    """Set classification codes"""
    if data is None:
        Logger.warning("No classification codes provided")
        return None
    #
    idS = list()
    if data.get("classification"):
        idS.append(etree.SubElement(inTree, TEI + "classCode"))
        idS[-1].set("scheme", "classification")
        idS[-1].text = data.get("classification")
    if data.get("acm"):
        idS.append(etree.SubElement(inTree, TEI + "classCode"))
        idS[-1].set("scheme", "acm")
        idS[-1].text = data.get("acm")
    if data.get("mesh"):
        idS.append(etree.SubElement(inTree, TEI + "classCode"))
        idS[-1].set("scheme", "mesh")
        idS[-1].text = data.get("mesh")
    if data.get("jel"):
        idS.append(etree.SubElement(inTree, TEI + "classCode"))
        idS[-1].set("scheme", "jel")
        idS[-1].text = data.get("jel")
    halDomains = data.get("halDomain")
    if halDomains:
        if type(halDomains) != list:
            halDomains = [halDomains]
        for id, d in enumerate(halDomains):
            idS.append(etree.SubElement(inTree, TEI + "classCode"))
            if id == 0:
                idS[-1].set("scheme", "halDomain")
            else:
                idS[-1].set("scheme", "halDomain")
            idS[-1].set("n", d)
    return idS


def getTypeDoc(typeDoc):
    """Get type of document"""
    if typeDoc is None:
        Logger.warning("No type of document provided")
        return None
    typeDoc = typeDoc.lower()
    if (
        typeDoc == "article"
        or typeDoc == "journalarticle"
        or typeDoc == "articlejournal"
        or typeDoc == "art"
    ):  # Article dans une revue
        return "ART"
    elif (
        typeDoc == "articlereview"
        or typeDoc == "review"
        or typeDoc == "artrev"
        or typeDoc == "articlesynthese"
    ):  # Article de synthèse
        return "ARTREV"
    elif typeDoc == "datapaper" or typeDoc == "paperdata":  # Cdata paper
        return "DATAPAPER"
    elif (
        typeDoc == "bookreview" or typeDoc == "compterendulecture"
    ):  # Compte rendu de lecture
        return "BOOKREVIEW"
    elif (
        typeDoc == "comm"
        or typeDoc == "conferencePaper"
        or typeDoc == "communication"
        or typeDoc == "conference"
    ):  # Communication dans un congrés
        return "COMM"
    elif typeDoc == "poster":  # poster de conference
        return "POSTER"
    elif (
        typeDoc == "proceedings" or typeDoc == "recueilcommunications"
    ):  # Proceedings\/Recueil des communication
        return "PROCEEDINGS"
    elif (
        typeDoc == "issue" or typeDoc == "specialissue" or typeDoc == "numerospecial"
    ):  # Numéro spécial
        return "ISSUE"
    elif (
        typeDoc == "ouv"
        or typeDoc == "book"
        or typeDoc == "monograph"
        or typeDoc == "ouvrage"
    ):  # Ouvrage
        return "OUV"
    elif typeDoc == "crit" or typeDoc == "editioncritique":  # Edition critique
        return "CRIT"
    elif typeDoc == "manual" or typeDoc == "manuel":  # Manuel
        return "MANUAL"
    elif typeDoc == "syntouv" or typeDoc == "ouvragesynthese":  # Ouvrage de synthese
        return "SYNTOUV"
    elif (
        typeDoc == "dictionary"
        or typeDoc == "dictionnaire"
        or typeDoc == "encyclopedie"
    ):  # Dictionnaire ou encyclopédie
        return "DICTIONARY"
    elif typeDoc == "couv" or typeDoc == "chapitre":  # Chapitre d'ouvrage
        return "COUV"
    elif typeDoc == "blog" or typeDoc == "articleblog":  # Article de blog scientifique
        return "BLOG"
    elif (
        typeDoc == "notice"
        or typeDoc == "noticedictionary"
        or typeDoc == "noticeencyclopede"
    ):  # Notice de dictionnaire ou d'encyclopedie
        return "NOTICE"
    elif typeDoc == "trad" or typeDoc == "traduction":  # traduction
        return "TRAD"
    elif typeDoc == "patent" or typeDoc == "brevet":  # brevet
        return "PATENT"
    elif typeDoc == "other" or typeDoc == "autre":  # autre document scientifique
        return "OTHER"
    elif (
        typeDoc == "undefined"
        or typeDoc == "prepublication"
        or typeDoc == "documenttravail"
    ):  # pré-publication/document de travail
        return "UNDEFINED"
    elif (
        typeDoc == "preprint" or typeDoc == "prepublication"
    ):  # preprint/pre-publication
        return "PREPRINT"
    elif typeDoc == "workingpaper":  # working paper
        return "WORKINGPAPER"
    elif (
        typeDoc == "creport"
        or typeDoc == "chapitrerapport"
        or typeDoc == "chaptereport"
    ):  # chapitre de rapport
        return "CREPORT"
    elif typeDoc == "report" or typeDoc == "rapport":  # rapport
        return "REPORT"
    elif (
        typeDoc == "resreport"
        or typeDoc == "rapportrecherche"
        or typeDoc == "researchreport"
    ):  # rapport de recherche
        return "RESREPORT"
    elif (
        typeDoc == "techreport"
        or typeDoc == "rapporttechnique"
        or typeDoc == "technicalreport"
    ):  # rapport technique
        return "TECHREPORT"
    elif (
        typeDoc == "fundreport"
        or typeDoc == "rapportcontrat"
        or typeDoc == "rapportprojet"
        or typeDoc == "contractreport"
        or typeDoc == "projectreport"
    ):  # rapport de contrat/projet
        return "FUNDREPORT"
    elif (
        typeDoc == "expertreport" or typeDoc == "rapportexpertise"
    ):  # rapport d'une expertise collective
        return "EXPERTREPORT"
    elif (
        typeDoc == "dmp" or typeDoc == "plangestiondonnees"
    ):  # data management plan/plan gestion de données
        return "DMP"
    elif typeDoc == "these" or typeDoc == "theses":  # these
        return "THESE"
    elif typeDoc == "hdr" or typeDoc == "habilitation":  # HDR
        return "HDR"
    elif typeDoc == "lecture" or typeDoc == "cours":  # cours
        return "LECTURE"
    elif typeDoc == "mem" or typeDoc == "memoire":  # mémoire étudiant
        return "MEM"
    elif typeDoc == "img" or typeDoc == "image" or typeDoc == "picture":  # image
        return "IMG"
    elif (
        typeDoc == "photography" or typeDoc == "photo" or typeDoc == "photographie"
    ):  # photographie
        return "PHOTOGRAPHY"
    elif typeDoc == "drawing" or typeDoc == "dessin":  # dessin
        return "DRAWING"
    elif typeDoc == "illustration":  # illustration
        return "ILLUSTRATION"
    elif typeDoc == "gravure":  # gravure
        return "GRAVURE"
    elif typeDoc == "graphics":  # image de synthèse
        return "GRAPHICS"
    elif typeDoc == "video" or typeDoc == "movie":  # video
        return "VIDEO"
    elif typeDoc == "son" or typeDoc == "sound":  # son
        return "SON"
    elif typeDoc == "software" or typeDoc == "logiciel":  # logiciel
        return "SOFTWARE"
    elif typeDoc == "presconf":  # Document associé à des manifestations scientifiques
        return "PRESCONF"
    elif typeDoc == "software" or typeDoc == "logiciel":  # logiciel
        return "ETABTHESE"
    elif typeDoc == "memclic":  #
        return "MEMLIC"
    elif typeDoc == "note":  # note de lecture
        return "NOTE"
    elif (
        typeDoc == "otherreport" or typeDoc == "autrerapport"
    ):  # autre rapport, séminaire...
        return "OTHERREPORT"
    elif typeDoc == "repact" or typeDoc == "rapportactivite":  # rapport d'activité
        return "REPACT"
    elif typeDoc == "synthese" or typeDoc == "notesynthese":  # notes de synthèse
        return "SYNTHESE"
    else:
        Logger.warning("Unknown type of document: force article")
        return "ART"


def setType(inTree, typeDoc=None):
    """Set type of document"""
    if typeDoc:
        idT = etree.SubElement(inTree, TEI + "classCode")
        idT.set("scheme", "halTypology")
        idT.set("n", getTypeDoc(typeDoc))
    return idT


def getStructType(name):
    """Try to identified the structure type from name"""
    if name is None:
        Logger.debug("No name for structure")
        return None
    else:
        name = unidecode(name.lower())  # remove accent and get lower case
        if (
            "université" in name
            or "university" in name
            or "univ" in name
            or "école" in name
            or "school" in name
        ):
            return "institution"
        elif "laboratoire" in name or "laboratory" in name or "lab" in name:
            return "institution" #"laboratory" (must be declared with dependency to an institution)
        elif "institute" in name or "institution" in name:
            return "institution"
        elif "department" in name or "departement" in name:
            return "institution"
        elif "team" in name:
            return "researchteam"


def setAddress(inTree, address):
    """Set an address in XML"""
    if address is None:
        Logger.debug("No address for structure")
        return None
    # different inputs address form
    addressLine = None
    addressCountry = None
    addressCountryCode = None
    if type(address) == str:
        addressLine = address
    elif type(address) == dict:
        addressLine = address.get("line", None)
        addressCountry = address.get("country", None)
    # get country name in plain text in string
    if addressCountry is None:
        addressCountry = m.getCountryFromText(address)
    # get country code
    addressCountryCode = m.getAlpha2Country(addressCountry)
    # set address
    idA = list()
    idA.append(etree.SubElement(inTree, TEI + "addrLine"))
    idA[-1].text = addressLine
    if addressCountryCode is not None:
        idA.append(etree.SubElement(inTree, TEI + "country"))
        idA[-1].set("key", addressCountryCode)
    if addressCountry:
        idA[-1].text = addressCountry
    return idA


def setStructure(inTree, data, id=None):
    """Set a structure in XML"""
    if data is None:
        Logger.debug("No data for structure")
        return None
    orgType = data.get("type", None)
    if orgType is None:
        orgType = getStructType(data.get("name", None))
        if orgType is None:
            orgType = dflt.DEFAULT_STRUCT_TYPE
    idS = etree.SubElement(inTree, TEI + "org")
    idS.set("type", orgType)
    if data.get("id", None) is None:
        Logger.warning(
            "No id for structure {}: force manual {}".format(data.get("name", None), id)
        )
    idS.set(dflt.DEFAULT_XML_LANG + "id", "localStruct-" + data.get("id", str(id)))
    idD = etree.SubElement(idS, TEI + "orgName")
    idD.text = data.get("name")
    if data.get("acronym", None):
        idD = etree.SubElement(idS, TEI + "orgName")
        idD.set("type", "acronym")
        idD.text = data.get("acronym")
    if data.get("address", None) or data.get("url", None):
        idD = etree.SubElement(idS, TEI + "desc")
    if data.get("address", None):
        idA = etree.SubElement(idD, TEI + "address")
        idS = setAddress(idA, data.get("address"))
    if data.get("url", None):
        idU = etree.SubElement(idD, TEI + "ref")
        idU.set("type", "url")
        idU.set("target", data.get("url"))
    return idS


def setStructures(inTree, data):
    """Set all structures in XML"""
    if data is None : 
        Logger.debug("No structures provided")
        return None
    # if no dictionary: one structure
    if type(data) != list:
        data = [data]
    # set all structures
    idSS = etree.SubElement(inTree, TEI + "listOrg")
    idSS.set("type", "structures")
    idA = list()
    for i in data:
        idA.append(setStructure(idSS, i))
    return idA


def setEditors(inTree, data):
    """Set scientific editor(s) in XML"""
    if data is None:
        Logger.debug("No scientific editor(s) provided")
        return None
    if type(data) != list:
        data = [data]
    listId = list()
    for i in data:
        listId.append(etree.SubElement(inTree, TEI + "editor"))
        listId[-1].text = i
    return listId


def setInfoDoc(inTree, data):
    """Set info of the document (publisher, serie, volume...) in XML"""
    if data is None:
        Logger.debug("No document info provided")
        return None
    #
    listId = list()
    dataPublisher = data.get("publisher", None)
    if dataPublisher:
        if type(dataPublisher) != list:
            dataPublisher = [dataPublisher]
        for p in dataPublisher:
            listId.append(etree.SubElement(inTree, TEI + "publisher"))
            listId[-1].text = p
    if data.get("serie", None):
        listId.append(etree.SubElement(inTree, TEI + "biblScope"))
        listId[-1].set("unit", "serie")
        listId[-1].text = data.get("serie")
    if data.get("volume", None):
        listId.append(etree.SubElement(inTree, TEI + "biblScope"))
        listId[-1].set("unit", "volume")
        listId[-1].text = data.get("volume")
    if data.get("issue", None):
        listId.append(etree.SubElement(inTree, TEI + "biblScope"))
        listId[-1].set("unit", "issue")
        listId[-1].text = data.get("issue")
    if data.get("pages", None):
        listId.append(etree.SubElement(inTree, TEI + "biblScope"))
        listId[-1].set("unit", "pp")
        listId[-1].text = data.get("pages")
    if data.get("datePub", None):
        listId.append(etree.SubElement(inTree, TEI + "date"))
        listId[-1].set("type", "datePub")
        listId[-1].text = data.get("datePub")
    if data.get("dateEpub", None):
        listId.append(etree.SubElement(inTree, TEI + "date"))
        listId[-1].set("type", "dateEpub")
        listId[-1].text = data.get("dateEpub")
    if data.get("whenWritten", None):
        listId.append(etree.SubElement(inTree, TEI + "date"))
        listId[-1].set("type", "whenWritten")
        listId[-1].text = data.get("whenWritten")
    if data.get("whenSubmitted", None):
        listId.append(etree.SubElement(inTree, TEI + "date"))
        listId[-1].set("type", "whenSubmitted")
        listId[-1].text = data.get("whenSubmitted")
    if data.get("whenReleased", None):
        listId.append(etree.SubElement(inTree, TEI + "date"))
        listId[-1].set("type", "whenReleased")
        listId[-1].text = data.get("whenReleased")
    if data.get("whenProduced", None):
        listId.append(etree.SubElement(inTree, TEI + "date"))
        listId[-1].set("type", "whenProduced")
        listId[-1].text = data.get("whenProduced")
    return listId


def setSeries(inTree, data):
    """Set series (book, proceedings...) in XML"""
    if data is None:
        Logger.debug("No series provided")
        return None
    #
    listId = list()
    if data.get("editor", None):
        listId.append(etree.SubElement(inTree, TEI + "editor"))
        listId[-1].text = data.get("editor")
    if data.get("title", None):
        listId.append(etree.SubElement(inTree, TEI + "title"))
        listId[-1].text = data.get("title")
    return listId


def setRef(inTree, data):
    """Set external references in XML"""
    if data is None:
        Logger.debug("No external reference provided")
        return None
    #
    items = [
        "doi",
        "arxiv",
        "bibcode",
        "ird",
        "pubmed",
        "ads",
        "pubmedcentral",
        "irstea",
        "sciencespo",
        "oatao",
        "ensam",
        "prodinra",
    ]
    listId = list()
    for it in items:
        if data.get(it, None):
            listId.append(etree.SubElement(inTree, TEI + "idno"))
            listId[-1].set("type", it)
            listId[-1].text = data.get(it)
    items = ["publisher"]
    items.extend(["link" + str(i) for i in range(0, 10)])
    for it in items:
        if data.get(it, None):
            listId.append(etree.SubElement(inTree, TEI + "ref"))
            if it == "publisher":
                listId[-1].set("type", it)
            else:
                listId[-1].set("type", "seeAlso")
            listId[-1].text = data.get(it)
    return listId


def buildXML(data):
    """Build the XML file from data"""
    Logger.debug("Open XML tree with namespace")

    # for k,v in dflt.DEFAULT_NAMESPACE_XML.items():
    #     if not k:
    #         k = ''
    #     etree.register_namespace(k, v)
    #
    tei = etree.Element(TEI + "TEI", nsmap=dflt.DEFAULT_NAMESPACE_XML)
    # tei.set("xmlns","http://www.tei-c.org/ns/1.0")
    # tei.set("xmlns:hal","http://hal.archives-ouvertes.fr/")
    Logger.debug("Add first elements")
    text = etree.SubElement(tei, TEI + "text")
    body = etree.SubElement(text, TEI + "body")
    listBibl = etree.SubElement(body, TEI + "listBibl")
    biblFull = etree.SubElement(listBibl, TEI + "biblFull")
    Logger.debug("Start to add metadata")
    # add title(s)/author
    Logger.debug("Add title(s) 1/2")
    titleStmt = etree.SubElement(biblFull, TEI + "titleStmt")
    title = setTitles(titleStmt, data.get("title", None), data.get("subtitle", None))
    Logger.debug("Add authors 1/2")
    authors = setAuthors(titleStmt, data.get("authors", None))
    # # add file
    # if data.get('file',None):
    #     Logger.debug('Add file')
    #     addFileInXML(biblFull,data.get('file'))
    # add licence
    if data.get("licence", None):
        Logger.debug("Add licence")
        publicationStmt = etree.SubElement(biblFull, TEI + "publicationStmt")
        setLicence(publicationStmt, data.get("licence"))
    # add notes
    if data.get("notes", None):
        Logger.debug("Add notes")
        setNotes(biblFull, data.get("notes"))
    ## new section
    sourceDesc = etree.SubElement(biblFull, TEI + "sourceDesc")
    biblStruct = etree.SubElement(sourceDesc, TEI + "biblStruct")
    analytic = etree.SubElement(biblStruct, TEI + "analytic")
    # add title(s)
    Logger.debug("Add title(s) 2/2")
    titleB = setTitles(analytic, data.get("title", None), data.get("subtitle", None))
    Logger.debug("Add authors 2/2")
    authorsB = setAuthors(analytic, data.get("authors", None))
    # add identifications data
    Logger.debug("Add identification numbers")
    monogr = etree.SubElement(biblStruct, TEI + "monogr")
    setIDS(monogr, data.get("ID", None))
    # add bib information relative to document
    Logger.debug("Add situation value for document")
    imprint = etree.SubElement(monogr, TEI + "imprint")
    setInfoDoc(imprint, data.get("infoDoc", None))
    # add series description for book, proceedings...
    Logger.debug("Add series description")
    series = etree.SubElement(biblStruct, TEI + "series")
    setSeries(series, data.get("series", None))
    # add external ref of document
    Logger.debug("Add external reference(s)")
    setRef(biblStruct, data.get("extref", None))
    # new section
    profileDesc = etree.SubElement(biblFull, TEI + "profileDesc")
    Logger.debug("Add language")
    setLanguage(profileDesc, data.get("lang", None))
    textClass = etree.SubElement(profileDesc, TEI + "textClass")
    # add keywords
    Logger.debug("Add keywords")
    setKeywords(textClass, data.get("keywords", None))
    # add classification codes
    Logger.debug("Add classification codes")
    setCodes(textClass, data.get("codes", None))
    # set type of document
    Logger.info("Add type of document: {}".format(data.get("type", None)))
    setType(textClass, data.get("type", None))
    # add abstract(s)
    Logger.debug("Add abstract(s)")
    setAbstract(profileDesc, data.get("abstract", None))
    # new section
    back = etree.SubElement(text, TEI + "back")
    # add structure(s)
    Logger.debug("Add structure(s)")
    setStructures(back, data.get("structures", None))

    return tei
