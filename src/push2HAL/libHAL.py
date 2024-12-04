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
import os
import sys
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
from . import libAPIHAL as libapi

## create a custom logger
logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> |"
    "<red>PUSH2HAL</red> |"
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    #"{extra[ip]} {extra[user]} - <level>{message}</level>"
    "<level>{message}</level>"
)

logger.remove()
logger.add(sys.stderr, format=logger_format)


## get XML's namespace for everything
TEI = "{%s}" % dflt.DEFAULT_TEI_URL_NAMESPACE



def addFileInXML(inTree, filePath, hal_id="upload"):
    """Add new imported file in XML"""
    newFilename = dflt.DEFAULT_UPLOAD_FILE_NAME_PDF.format(hal_id)
    logger.debug("Copy original file to new one: {} -> {}".format(filePath, newFilename))
    shutil.copyfile(filePath, newFilename)
    # find section to add file
    inS = inTree.find(".//editionStmt", inTree.nsmap)
    if inS is None:
        newE = addElementinTree(inTree, None, "editionStmt")  # , nsmap=inTree.nsmap)
        pos = inTree.find(".//titleStmt", inTree.nsmap)
        pos.addnext(newE)
        inS = inTree.find(".//editionStmt", inTree.nsmap)
    # find subsection
    inSu = inS.find(".//edition", inTree.nsmap)
    if inSu is None:
        inSu = addElementinTree(inS, None, "edition") #, nsmap=inTree.nsmap)

    # check existing file
    # nFile = inS.xpath("//ref[@type='file']") #find('.//ref',inTree.nsmap)
    # add file
    logger.debug("Add file in XML: {}".format(newFilename))
    _ = addElementinTree(inSu, None, "ref",
                             attr_unique={"type": "file", "subtype": "author", "n": "1", "target": newFilename})
    return newFilename




def buildZIP(xml_file_path, pdf_file_path):
    """Build ZIP archive for HAL deposit (containing XML and PDF)"""
    # create temporary directory
    tmp_dir_path = tempfile.mkdtemp()
    logger.debug("Create temporary directory: {}".format(tmp_dir_path))
    xml_file_dst = os.path.join(tmp_dir_path, dflt.DEFAULT_UPLOAD_FILE_NAME_XML)
    logger.debug("Copy XML file: {} -> {}".format(xml_file_path, xml_file_dst))
    shutil.copy(xml_file_path, xml_file_dst)
    logger.debug("Copy PDF file: {} -> {}".format(pdf_file_path, tmp_dir_path))
    shutil.copy(pdf_file_path, tmp_dir_path)
    # build zip archive
    archivePath = dflt.DEFAULT_UPLOAD_FILE_NAME_ZIP
    logger.debug("Create zip archive: {}".format(archivePath + ".zip"))
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
        # m.cleanXML(tei_content, ".//idno[@type='stamp']")
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
    header["Packaging"] = m.adaptH(dflt.DEFAULT_XML_SWORD_PACKAGING.url)
    header["X-test"] = m.adaptH(options.get("testMode", dflt.DEFAULT_HAL_TEST))
    if header["X-test"] == "1":
        logger.warning("Test mode activated")
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


def upload2HAL(file, headers=None, hal_id=None,credentials=None, server="preprod"):
    """Upload to HAL"""
    logger.info("Upload to HAL")
    logger.debug("File: {}".format(file))
    logger.debug("Headers: {}".format(headers))

    if server == "preprod":
        url = dflt.HAL_SWORD_PRE_API_URL
    else:
        url = dflt.HAL_SWORD_API_URL

    logger.debug("Upload via {}".format(url))
    # read data to sent
    with open(file, "rb") as f:
        data = f.read()
    if not hal_id:
        res = requests.post(
            url=url,
            data=data,
            headers=headers,
            auth=HTTPBasicAuth(credentials["login"], credentials["passwd"]),
        )
    else:
        # reove last segement on url 
        url.remove(path='hal/')
        # append id_hal of the decument
        id = hal_id.split('v')[0]
        url = url / id
        #
        res = requests.put(
            url=url,
            data=data,
            headers=headers,
            auth=HTTPBasicAuth(credentials["login"], credentials["passwd"]),
        )
    
     
    hal_id = res.status_code
    if res.status_code == 201 or res.status_code == 200:
        logger.info("Successfully upload to HAL.")
        # read return message
        xmlResponse = etree.fromstring(res.text.encode("utf-8"))
        elem = xmlResponse.findall("id", xmlResponse.nsmap)
        hal_id = elem[0].text
        logger.debug("HAL ID: {}".format(elem[0].text))
    elif res.status_code == 202:
        logger.info("Note accepted by HAL.")
        # read return message
        xmlResponse = etree.fromstring(res.text.encode("utf-8"))
        elem = xmlResponse.findall("id", xmlResponse.nsmap)
        hal_id = elem[0].text
        logger.debug("HAL ID: {}".format(elem[0].text))
    elif res.status_code == 401:
        logger.info("Authentification refused - check credentials")
    else:
        # read error message
        xmlResponse = etree.fromstring(res.text.encode("utf-8"))
        elem = xmlResponse.findall(
            dflt.DEFAULT_ERROR_DESCRIPTION_SWORD_LOC, xmlResponse.nsmap
        )
        logger.error("Failed to upload. Status code: {}".format(res.status_code))
        if len(elem) > 0:
            json_ret = list()
            for i in elem:
                content = None
                try:
                    if isinstance(i.text, str):
                        content = i.text
                    else:
                        content = json.loads(i.text)
                except:
                    pass
                if content is None:
                    content = i.text
                json_ret.append(content)
                logger.warning("Error: {}".format(i.text))
        # extract hal_id
        for j in json_ret:
            if type(j) is dict:
                if j.get('duplicate-entry'):                    
                    hal_id = list(j.get('duplicate-entry').keys())[0]
                    logger.warning('Duplicate entry: {}'.format(hal_id))
    return hal_id

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

def setTitles(nInTree, titles, 
              subTitles=None,
              cleartitle=False,
              clearsubtitle=False):
    """Add title(s) and subtitle(s) in XML (and specified language)"""
    # clear existing titles/subtitles
    if not titles and not subTitles:
        logger.warning("No title nor subtitle provided")
        return None
    if clearsubtitle:
        removeElementinTree(nInTree, "title", 
                            attr={"type": "sub"})
    if cleartitle:
        removeElementinTree(nInTree, "title", 
                            nattr={"type": "main"})
    # prepare data
    if subTitles:
        listTitles = {"titles": titles, "subtitles": subTitles}
    else:
        listTitles = {"titles": titles}
    nTitle = list()
    # add titles/subtitles
    for k, n in listTitles.items():
        if isinstance(n, str):
            n = {"en": n}
        for lang, t in n.items():            
            attr_content = {dflt.DEFAULT_XML_LANG + "lang": lang}
            if k == "subtitles":
                attr_content["type"] = "sub"
            
            nTitle.append(addElementinTree(nInTree,t,
                                      "title", 
                                      attr_unique=attr_content, 
                                      remove_empty_data=True))
    return nTitle


def getNameFormated(a):
    """format name from dict to list"""
    listName = [a["firstname"]]
    listName.append(a.get("middle", None))
    listName.append(a["lastname"])
    listName = list(filter(None, listName))
    return listName


def setAuthors(inTree, authors, clear=False):
    """Add authors in XML (and linked to affiliation)"""
    if not authors:
        logger.warning("No author provided")
        return None
    # clear authors
    if clear:
        removeElementinTree(inTree, "author")
    # add authors
    nAuthors = list()
    for a in authors:
        # format name
        nameFormated = getNameFormated(a)        
        # roles: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:relator&fl=*&wt=xml
        if a.get('role', None):   
            attr_built = {"role": a["role"]}
        else:
            logger.warning(
                "No role for author {} {}: force aut".format(
                    nameFormated[0], nameFormated[-1]
                )
            )
            attr_built = {"role": "aut"}
        nAuthors.append(addElementinTree(inTree, None, "author", attr_unique=attr_built))
        persName = addElementinTree(nAuthors[-1], None, "persName")
        _ = addElementinTree(persName, nameFormated[0], "forename", attr_unique={"type": "first"})
        if len(nameFormated) > 2:
            _ = addElementinTree(persName, nameFormated[1], "forename", attr_unique={"type": "middle"})
        _ = addElementinTree(persName, nameFormated[-1], "surname")
        if a.get("email", None):
            _ = addElementinTree(nAuthors[-1], a["email"], "email")
        if a.get("idhal", None):
            _ = addElementinTree(nAuthors[-1], a["idhal"], "idno", attr_unique={"type": "idhal"})
        if a.get("halauthor", None):
            _ = addElementinTree(nAuthors[-1], a["halauthor"], "idno", attr_unique={"type": "halauthor"})
        if a.get("url", None):
            _ = addElementinTree(nAuthors[-1], None, "ptr", 
                                   attr_unique={"type": "url", "target": a["url"]})
        if a.get("orcid", None):
            _ = addElementinTree(nAuthors[-1], a["orcid"], "idno", 
                                   attr_unique={"type": dflt.ID_ORCID_URL.url})
        if a.get("arxiv", None):
            _ = addElementinTree(nAuthors[-1], a["arxiv"], "idno", 
                                   attr_unique={"type": dflt.ID_ARXIV_URL})
        if a.get("researcherid", None):
            _ = addElementinTree(nAuthors[-1], a["researcherid"], "idno", 
                                   attr_unique={"type": dflt.ID_RESEARCHERID_URL})
        if a.get("idref", None):
            _ = addElementinTree(nAuthors[-1], a["idref"], "idno", 
                                   attr_unique={"type": dflt.ID_IDREF_URL})
        if a.get("affiliation", None):
            if type(a["affiliation"]) is not list:
                list_aff = [a["affiliation"]]
            else:
                list_aff = a["affiliation"]
            for aff in list_aff:
                _ = addElementinTree(nAuthors[-1], None, "affiliation", 
                                        attr_unique={"ref": "#localStruct-" + aff})
        if a.get("affiliationHAL", None):
            if type(a["affiliationHAL"]) is not list:
                list_aff = [a["affiliationHAL"]]
            else:
                list_aff = a["affiliationHAL"]
            for aff in list_aff:                
                idStrut = aff
                idStruct = re.sub("^#struct-", "", idStrut)
                _ = addElementinTree(nAuthors[-1], None, "affiliation", attr_unique={"ref": idStruct})
    return nAuthors


def setLicence(inTree, licence, clear = False):
    """Set licence in XML"""
    if not licence:
        logger.warning("No licence provided")
        return None
    # clear licence
    if clear:
        removeElementinTree(inTree, "licence")
    # add licence
    availability = addElementinTree(inTree, None, "availability")
    # all licences: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:licence&fl=*&wt=xml
    if type(licence) is dict:
        licenceV = licence["licence"]
    else:
        licenceV = licence
    logger.warning("licence: {} (works only for Creative Commons one)".format(licenceV))
    buildURL = dflt.ID_CC_URL / licenceV / "/"
    lic_cc = addElementinTree(availability, None, "licence", attr_unique={'target': buildURL.url})
    return lic_cc


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
    if not notes:
        logger.warning("No licence provided")
        return None
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
        logger.warning(
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
        logger.warning(
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
        logger.warning(
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
        logger.warning(
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
        logger.warning(
            "Unknown proceedings status: force default ({})".format(
                dflt.DEFAULT_PROCEEDINGS
            )
        )
        proFlag = dflt.DEFAULT_PROCEEDINGS
    return proFlag


def setNotes(inTree, notes, clear=False):
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
    if not notes:
        logger.warning("No notes provided")
        return None
    # clear notes
    if clear:
        removeElementinTree(inTree, "notesStmt")
    nNotes = list()
    # add element for notes
    idN = addElementinTree(inTree, None, "notesStmt")
    # define audience
    nNotes.append(addElementinTree(idN, None, "note", 
                  attr_unique={"type": "audience", "n": getAudience(notes)}))
    # define invited
    nNotes.append(addElementinTree(idN, None, "note", 
                  attr_unique={"type": "invited", "n": getInvited(notes)}))
    # define popular
    nNotes.append(addElementinTree(idN, None, "note",
                  attr_unique={"type": "popular", "n": getPopular(notes)}))
    # define peer
    nNotes.append(addElementinTree(idN, None, "note",
                  attr_unique={"type": "peer", "n": getPeer(notes)}))
    # define proceedings
    nNotes.append(addElementinTree(idN, None, "note",
                  attr_unique={"type": "proceedings", "n": getProceedings(notes)}))

    if notes.get("comment", None):
        nNotes.append(addElementinTree(idN, notes.get("comment"), "note",
                                       attr_unique={"type": "commentary"},
                                       remove_empty_data=True))
    if notes.get("description", None):
        nNotes.append(addElementinTree(idN, notes.get("description"), "note",
                                       attr_unique={"type": "description"},
                                       remove_empty_data=True))
    return nNotes


def setAbstract(inTree, abstracts, clear=False):
    """Add abstract in XML (and specified language)"""
    # clear abstract
    if clear:
        removeElementinTree(inTree, "abstract")
    if abstracts is None:
        logger.warning("No provided abstract")
        return None
    nAbstract = list()
    if isinstance(abstracts, str):
        logger.warning("No language for abstract: force english")
        nAbstract.append(addElementinTree(inTree, abstracts, "abstract",
                                          attr_unique={dflt.DEFAULT_XML_LANG + "lang": "en"},
                                          remove_empty_data=True)) 
    else:
        for lk, vk in abstracts.items():
            nAbstract.append(addElementinTree(inTree, vk, "abstract",
                                              attr_unique={dflt.DEFAULT_XML_LANG + "lang": lk},))
    return nAbstract


def setID(inTree, ids, typeId):
    """Add ID of document using idno"""
    idT = None
    if ids:
        idT = addElementinTree(inTree, ids, "idno", 
                               attr_unique={"type": typeId})
    return idT


def setIDS(inTree, data, clear=False):
    """Set all IDs"""
    if not data:
        logger.warning("No ID provided")
        return None
    # clear IDs
    if clear:
        removeElementinTree(inTree, "idno")
    # set IDs
    lID = []
    if data.get("nnt", None):
        lID.append(setID(inTree, data.get("nnt"), "nnt"))
    if data.get("isbn", None):
        if not isbn.is_valid(data.get("isbn")):
            logger.warning("ISBN not valid: {}, continue...".format(data.get("isbn")))
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
            api = libapi.APIHALjournal()
            idJ = api.search(
                query={"title": data.get("journal")},
                returnFields=["docid","title_s"],
                returnFormat="json",
            )
            if idJ is None:
                idJ = api.search(
                query={"title_approx": data.get("journal")},
                returnFields=["docid","title_s"],
                returnFormat="json",
            )
            # adapt id if many are found
            idJournal = None
            if len(idJ) > 1:
                logger.debug("Identify write journal ID in HAL")
                listJ = [j["title_s"] for j in idJ]
                jName = difflib.get_close_matches(data.get("journal"), listJ)
                ixJ = listJ.index(jName[0])
                idJournal = idJ[ixJ]["docid"]
            if idJournal:
                logger.debug("Jounal ID found: {}".format(idJournal))
                lID.append(setID(inTree, idJournal, "halJournalId"))
    if data.get("issn", None):
        if not issn.is_valid(data.get("issn")):
            logger.warning("ISSN not valid: {}, continue...".format(data.get("issn")))
    lID.append(setID(inTree, data.get("issn"), "issn"))
    if data.get("eissn", None):
        if not issn.validate(data.get("eissn")):
            logger.warning("eISSN not valid: {}, continue...".format(data.get("eissn")))
    lID.append(setID(inTree, data.get("eissn"), "eissn"))
    if data.get("j", None):
        lID.append(addElementinTree(inTree,data.get("j"), "title", attr_unique={"level": "j"}))
    if data.get("m", None):
        lID.append(addElementinTree(inTree,data.get("m"), "title", attr_unique={"level": "m"}))
    if data.get("booktitle", None):
        lID.append(addElementinTree(inTree,data.get("booktitle"), "title", attr_unique={"level": "m"}))
    if data.get("source", None):
        lID.append(addElementinTree(inTree,data.get("source"), "title", attr_unique={"level": "m"}))
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
        if not isinstance(dataORG, list):
            dataORG = [dataORG]
            for d in dataORG:
                idT = etree.SubElement(idM, TEI + "name")
                idT.text = d

    return []


def setLanguage(inTree, language, clear=False):
    """Set main language in XML"""
    # clear language
    idL= None
    if clear:
        removeElementinTree(inTree, "langUsage")
    langUsage = addElementinTree(inTree, None, "langUsage")
    if language is None and len(getElement(langUsage, "language")) == 0:
        logger.warning("No language provided - force {}".format(dflt.DEFAULT_LANG_DOC))
        language = dflt.DEFAULT_LANG_DOC
    if language is not None and len(getElement(langUsage, "language")) == 0:
        idL = addElementinTree(langUsage,None, "language", attr_unique={"ident": language})
    return idL


def setKeywords(inTree, keywords, clear=False):
    """Set keywords in XML (and specified language)"""
    # clear keywords
    if clear:
        removeElementinTree(inTree, "keywords")
    if keywords is None:
        logger.warning("No keywords provided")
        return None
    #
    if isinstance(keywords, str):
        keywords = [keywords]
    itK = addElementinTree(inTree, None, 
                           "keywords", 
                           attr_unique={"scheme": "author"})
    if isinstance(keywords, list):
        logger.warning("No language for keywords: force english")
        nKeywords = list()
        for k in keywords:
            nKeywords.append(addElementinTree(inTree, k, "keyword",
                                              attr_unique={dflt.DEFAULT_XML_LANG + "lang": "en"},
                                              force=True,
                                              remove_empty_data=True))
    else:
        nKeywords = list()
        for lk, vk in keywords.items():
            if not isinstance(vk, list):
                vk = [vk]
            for i in vk:
                nKeywords.append(addElementinTree(itK, i, "term", 
                                                  attr_unique={dflt.DEFAULT_XML_LANG + "lang": lk},
                                                  force=True,
                                                  remove_empty_data=True))

    return nKeywords


def setCodes(inTree, data, clear=False):
    """Set classification codes"""
    # clear codes
    if clear:
        removeElementinTree(inTree, "classCode")
    if data is None:
        logger.warning("No classification codes provided")
        return None
    #
    idS = list()
    if data.get("classification"):
        idS.append(addElementinTree(inTree, data.get("classification"), "classCode",
                                    attr_unique={"scheme": "classification"}))
    if data.get("acm"):
        idS.append(addElementinTree(inTree, data.get("acm"), "classCode",
                                    attr_unique={"scheme": "acm"}))
    if data.get("mesh"):
        idS.append(addElementinTree(inTree, data.get("mesh"), "classCode",
                                    attr_unique={"scheme": "mesh"}))
    if data.get("jel"):
        idS.append(addElementinTree(inTree, data.get("jel"), "classCode",
                                    attr_unique={"scheme": "jel"}))
    halDomains = data.get("halDomain")
    if halDomains:
        if not isinstance(halDomains, list):
            halDomains = [halDomains]
        for id, d in enumerate(halDomains):            
            idS.append(addElementinTree(inTree, None, "classCode",
                                        attr_unique={"scheme": "halDomain", "n": d}))
    return idS


def getTypeDoc(typeDoc):
    """Get type of document"""
    if typeDoc is None:
        logger.warning("No type of document provided")
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
    elif typeDoc == "etabthese":  # thèse d'établissement
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
        logger.warning("Unknown type of document: force article")
        return "ART"


def setType(inTree, typeDoc=None):
    """Set type of document"""
    idT = None
    if typeDoc:
        idT = addElementinTree(inTree, None, "classCode", 
                               attr_unique={"scheme": "halTypology", "n": getTypeDoc(typeDoc)})
    return idT


def getStructType(name):
    """Try to identified the structure type from name"""
    if name is None:
        logger.debug("No name for structure")
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
        logger.debug("No address for structure")
        return None
    # different inputs address form
    addressLine = None
    addressCountry = None
    addressCountryCode = None
    if isinstance(address, str):
        addressLine = address
    elif isinstance(address, dict):
        addressLine = address.get("line", None)
        addressCountry = address.get("country", None)
    # get country name in plain text in string
    if addressCountry is None:
        addressCountry = m.getCountryFromText(address)
    # get country code
    addressCountryCode = m.getAlpha2Country(addressCountry)
    # set address
    idA = list()
    idA.append(addElementinTree(inTree, addressLine, "addrLine"))
    if addressCountryCode is not None:
        idA.append(addElementinTree(inTree, addressCountry, "country",
                                    attr_unique={"key": addressCountryCode}))
    return idA


def setStructure(inTree, data, id=None):
    """Set a structure in XML"""
    if data is None:
        logger.debug("No data for structure")
        return None
    orgType = data.get("type", None)
    if orgType is None:
        orgType = getStructType(data.get("name", None))
        if orgType is None:
            orgType = dflt.DEFAULT_STRUCT_TYPE
    if data.get("id", None) is None:
        logger.warning(
            "No id for structure {}: force manual {}".format(data.get("name", None), id)
        )
    idS = addElementinTree(inTree, None, "org",
                        attr_unique={"type": orgType,
                                    dflt.DEFAULT_XML_LANG + "id": "localStruct-" + data.get("id", str(id))})
    idD = addElementinTree(idS, data.get("name"), "orgName")
    if data.get("acronym", None):
        idD = addElementinTree(idS, data.get("acronym"), "orgName", 
                               attr_unique={"type": "acronym"},
                               remove_empty_data=True)
    if data.get("address", None) or data.get("url", None):
        idD = addElementinTree(idS, None, "desc")
    if data.get("address", None):
        idA = addElementinTree(idD, None, "address")
        idS = setAddress(idA, data.get("address"))
    if data.get("url", None):
        _ = addElementinTree(idD, None, "ref",
                               attr_unique={"type": "url", "target": data.get("url")})
    return idS


def setStructures(inTree, data, clear=False):
    """Set all structures in XML"""
    # clear structures
    if clear:
        removeElementinTree(inTree, "listOrg")
    if data is None : 
        logger.debug("No structures provided")
        return None
    # if no dictionary: one structure
    if not isinstance(data, list):
        data = [data]
    # set all structures
    idSS = addElementinTree(inTree, None, "listOrg",
                            attr_unique={"type": "structures"})
    idA = list()
    for i in data:
        idA.append(setStructure(idSS, i))
    return idA


def setEditors(inTree, data):
    """Set scientific editor(s) in XML"""
    if data is None:
        logger.debug("No scientific editor(s) provided")
        return None
    if not isinstance(data, list):
        data = [data]
    listId = list()
    for i in data:
        listId.append(etree.SubElement(inTree, TEI + "editor"))
        listId[-1].text = i
    return listId


def setInfoDoc(inTree, data, clear=False):
    """Set info of the document (publisher, serie, volume...) in XML"""
    # clear info
    if data is None:
        logger.debug("No document info provided")
        return None
    #
    listId = list()
    dataPublisher = data.get("publisher", None)
    if dataPublisher:
        if not isinstance(dataPublisher, list):
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


def setSeries(inTree, data, clear=False):
    """Set series (book, proceedings...) in XML"""
    if data is None:
        logger.debug("No series provided")
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


def setRef(inTree, data, clear=False):
    """Set external references in XML"""
    # clear data
    if clear:
        removeElementinTree(inTree, "idno")
        removeElementinTree(inTree, "ref")
    if data is None:
        logger.debug("No external reference provided")
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
            listId.append(addElementinTree(inTree, data.get(it), "idno", 
                                           attr_unique={"type": it},
                                           remove_empty_data=True))
    items = ["publisher"]
    items.extend(["link" + str(i) for i in range(0, 10)])
    for it in items:
        if data.get(it, None):
            
            if it == "publisher":
                attr_built = {"type": it}
            else:
                attr_built = {"type": "seeAlso"}
            listId.append(addElementinTree(inTree, data.get(it), "ref", 
                                           attr_unique=attr_built,
                                           force=True,
                                           remove_empty_data=True))
    return listId

def getElement(inTree, tag, 
               attr=None, 
               nattr=None,
               strict=False, 
               namespace=TEI):
    """ Get element in XML tree """
    # find elements with tag
    elts = inTree.findall(".//{}".format(tag),inTree.nsmap)
    # find element with tag and unique attribute(s)
    if attr or nattr:
        elt = list()
        for e in elts:
            delete=False
            if attr:
                for k,v in attr.items():                
                    if strict:
                        if e.get(k) != v:                
                            delete = True
                            break
                    else:
                        if k not in e.attrib:
                            delete = True
                            break
            if nattr:
                for k,v in nattr.items():                
                    if strict:
                        if e.get(k) != v:                
                            delete = False
                            break
                    else:
                        if k not in e.attrib:
                            delete = False
                            break
            if not delete:
                elt.append(e)
    else:
        elt = elts
    return elt

def addElementinTree(inTree, data, tag, 
                     attr_unique=None,
                     attr=None, 
                     remove_empty_data=False,
                     clear=False,
                     force=False,
                     namespace=TEI):
    """ Add element or update it if not available """
    # find elements with tag and attribute()
    elt = getElement(inTree, tag, attr_unique, strict=True)
    if clear:
        inTree.remove(elt)
    # many elements
    if len(elt) > 1:
        logger.warning("Many elements found: {}".format(elt))
    elif len(elt) == 1:
        elt = elt[0]
    else:
        elt = None
    # force mode (in case of allowed duplicate elements)
    if force:
        elt = None
    #
    if elt is None:
        elt = etree.SubElement(inTree, namespace + tag)
    if attr_unique:
        for k,v in attr_unique.items():
            elt.set(k,v)
    if attr:
        for k,v in attr.items():
            elt.set(k,v)
    if data:
        elt.text = data
    elif remove_empty_data:
        inTree.remove(elt)
    
    return elt       

def removeElementinTree(inTree, tag, attr=None, nattr=None, namespace=TEI):
    """ Remove element in XML tree """
    elts = getElement(inTree, tag, attr, nattr)
    for e in elts:
        inTree.remove(e)
    return inTree
    


def buildXML(data, inTree=None):
    """Build the XML file from data"""
    logger.debug("Open XML tree with namespace")

    # for k,v in dflt.DEFAULT_NAMESPACE_XML.items():
    #     if not k:
    #         k = ''
    #     etree.register_namespace(k, v)
    # load existing XML tree
    if inTree:
        tei = inTree
    else:
        logger.debug('Create new XML tree')
        tei = etree.Element(TEI + "TEI", nsmap=dflt.DEFAULT_NAMESPACE_XML)
    # tei.set("xmlns","http://www.tei-c.org/ns/1.0")
    # tei.set("xmlns:hal","http://hal.archives-ouvertes.fr/")
    logger.debug("Add first elements")
    text = addElementinTree(tei, None, "text")
    body = addElementinTree(text, None, "body")
    listBibl = addElementinTree(body, None, "listBibl")
    biblFull = addElementinTree(listBibl, None, "biblFull")
    logger.debug("Start to add metadata")
    # add title(s)/author
    logger.debug("Add title(s) 1/2")
    titleStmt = addElementinTree(biblFull, None, "titleStmt")
    # add titles/subtitles
    _ = setTitles(titleStmt, 
                    data.get("title", None), 
                    data.get("subtitle", None),
                    cleartitle='title' in data.get('remove',[]),
                    clearsubtitle='subtitle' in data.get('remove',[])
                    )
    logger.debug("Add authors 1/2")
    _ = setAuthors(titleStmt, data.get("authors", None),
                         clear='authors' in data.get('remove',[]))
    # # add file
    # if data.get('file',None):
    #     logger.debug('Add file')
    #     addFileInXML(biblFull,data.get('file'))
    # add licence
    logger.debug("Add licence")
    publicationStmt = addElementinTree(biblFull, None, "publicationStmt")
    setLicence(publicationStmt, data.get("licence"),
                clear='licence' in data.get('remove',[]))
    # add notes
    logger.debug("Add notes")
    setNotes(biblFull, data.get("notes",None),
                clear='notes' in data.get('remove',[]))
    ## new section
    sourceDesc = addElementinTree(biblFull,None, "sourceDesc")
    biblStruct = addElementinTree(sourceDesc,None, "biblStruct")
    analytic = addElementinTree(biblStruct,None, "analytic")
    # add title(s)
    logger.debug("Add title(s) 2/2")
    _ = setTitles(analytic, 
                       data.get("title", None),
                       data.get("subtitle", None),
                       cleartitle='title' in data.get('remove',[]),
                       clearsubtitle='subtitle' in data.get('remove',[]))
    logger.debug("Add authors 2/2")
    _ = setAuthors(analytic, data.get("authors", None),
                          clear='authors' in data.get('remove',[]))
    # add identifications data
    logger.debug("Add identification numbers")
    monogr = addElementinTree(biblStruct, None, "monogr")
    setIDS(monogr, data.get("ID", None),
           clear='ID' in data.get('remove',[]))
    # add bib information relative to document
    logger.debug("Add situation value for document")
    imprint = addElementinTree(monogr, None, "imprint", 
                               clear='infoDoc' in data.get('remove',[]))
    setInfoDoc(imprint, data.get("infoDoc", None))
    # add series description for book, proceedings...
    logger.debug("Add series description")
    series = addElementinTree(biblStruct, None, "series",
                              clear='series' in data.get('remove',[]))
    setSeries(series, data.get("series", None))
    # add external ref of document
    logger.debug("Add external reference(s)")
    setRef(biblStruct, data.get("extref", None),
           clear='extref' in data.get('remove',[]))
    # new section
    profileDesc = addElementinTree(biblFull, None, "profileDesc")
    # add language
    logger.debug("Add language")
    setLanguage(profileDesc, data.get("lang", None),
                clear='lang' in data.get('remove',[]))
    # new section
    textClass = addElementinTree(profileDesc, None, "textClass")
    # add keywords
    logger.debug("Add keywords")
    setKeywords(textClass, data.get("keywords", None),
                clear='keywords' in data.get('remove',[]))
    # add classification codes
    logger.debug("Add classification codes")
    setCodes(textClass, data.get("codes", None),
             clear='codes' in data.get('remove',[]))
    # set type of document
    logger.info("Add type of document: {}".format(data.get("type", None)))
    setType(textClass, data.get("type", None))
    # add abstract(s)
    logger.debug("Add abstract(s)")
    setAbstract(profileDesc, data.get("abstract", None), 
                clear='abstract' in data.get('remove',[]))
    # new section
    back = addElementinTree(text, None, "back")
    # add structure(s)
    logger.debug("Add structure(s)")
    setStructures(back, data.get("structures", None), 
                  clear='structures' in data.get('remove',[]))

    return tei
