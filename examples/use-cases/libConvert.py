from pybliometrics.scopus import (
    AbstractRetrieval,
    AuthorRetrieval,
    AffiliationRetrieval,
)
import logging
from urllib.request import urlretrieve
import os
from habanero import Crossref
import json


cr = Crossref()

FORMAT = "LBCONVERT - %(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
Logger = logging.getLogger("lbconvert")



def findPDFurl(article):
    """Find PDF url from Scopus/ScienceDirect"""
    urlList = None
    urlList = article.get("url", None)
    return_value = None
    if urlList:
        for url in urlList:
            if url.get("format") == "pdf":
                return_value = url.get("value")
    return return_value


def buildAuthor(author):
    returnAuthor = dict()
    # get data of author from scopus
    autScopus = AuthorRetrieval(author.auid)
    # fill data
    returnAuthor["firstname"] = author.given_name
    returnAuthor["lastname"] = author.surname
    returnAuthor["affiliation"] = author.affiliation.split(";")
    Logger.debug("Author: {}".format(author))
    if autScopus.orcid:
        returnAuthor["orcid"] = autScopus.orcid

    return returnAuthor


def buildAuthors(authors):
    returnAuthors = list()
    for author in authors:
        returnAuthors.append(buildAuthor(author))
    return returnAuthors


def buildAffiliations(authorsData):
    # get full list of affiliations
    list_affiliations = set()
    for author in authorsData:
        for aff in author["affiliation"]:
            list_affiliations.add(aff)
    # renders list of affiliations
    returnAffiliations = list()
    for aff in list_affiliations:
        returnAffiliations.append(buildAffiliation(aff))
    return returnAffiliations


def buildAffiliation(affiliation):
    # get data from scopus
    affScopus = AffiliationRetrieval(affiliation)
    returnAffiliation = dict()
    returnAffiliation["id"] = affiliation
    returnAffiliation["name"] = affScopus.affiliation_name
    returnAffiliation["address"] = dict()
    dataAdress = list()
    if affScopus.address:
        dataAdress.append(affScopus.address)
    if affScopus.postal_code:
        dataAdress.append(affScopus.postal_code)
    if affScopus.city:
        dataAdress.append(affScopus.city)
    if affScopus.country:
        dataAdress.append(affScopus.country)
    returnAffiliation["address"]["line"] = ", ".join(dataAdress)
    returnAffiliation["address"]["country"] = affScopus.country
    returnAffiliation["url"] = affScopus.org_URL
    return returnAffiliation


def findURL(data):
    return_value = None
    for it in data:
        if it.get("content-type") == "text/html":
            return_value = it.get("URL")
            break
    return return_value


def cleanFilename(filename):
    """Clean filename"""
    return filename.replace("/", "_").replace(":", "_").replace(" ", "_")


def buildJSON(article, json_dir, pdf_dir=None):
    """Convert article data from Springer/Scopus to JSON specific format"""
    #
    download = True
    # get doi
    doi = article.get("doi", None)
    # data from crossref
    dataCrossRef = cr.works(ids=doi)
    # data from Scopus
    dataScopus = AbstractRetrieval(doi)
    #
    content = dict()

    if pdf_dir:
        # get pdf link and download
        pdf_link = findPDFurl(article)
        # pdf path
        pdf_path = os.path.join(pdf_dir, cleanFilename(doi) + ".pdf")
        # download
        if download:
            Logger.debug("Downloading PDF: {} -> {}".format(pdf_link, pdf_path))
            urlretrieve(pdf_link, pdf_path)

    # fill content
    content["type"] = "article"
    content["title"] = {"en": article["title"]}
    content["abstract"] = {"en": article["abstract"]}
    content["notes"] = {
        # "invited": "no",
        "audience": "international",
        "popular": "no",
        "peer": "yes",
        # "proceedings": "no",
        # "comment": "small comment",
        # "description": "small description"
    }
    content["ID"] = {
        # "isbn": "978-1725183483",
        # "patentNumber": "xxx",
        # "reportNumber": "xxx",
        # "locaRef": "xxx",
        # "haJournalId": "xxx", // HAL journal id (could be determine bu json2hal)
        "journal": article["publicationName"],
        "issn": dataCrossRef["message"]["ISSN"][0],
        "eissn": article["eIssn"],
        # "booktitle": "xxx",
        # "source": "xxx"
    }
    content["infoDoc"] = {
        "publisher": article["publisherName"],
        "volume": article["volume"],
        "issue": article["number"],
        "pages": article["startingPage"] + "-" + article["endingPage"],
        "serie": article["topicalCollection"],
        "datePub": article["publicationDate"],
        "dateEPub": article["onlineDate"],
    }
    content["extref"] = {
        "doi": article["doi"],
        # "arxiv": "ger",
        # "bibcode": "erg",
        # "ird": "greger",
        # "pubmed": "greger",
        # "ads": "gaergezg",
        # "pubmedcentral": "gegzefdv",
        # "irstea": "vvxc",
        # "sciencespo": "gderg",
        # "oatao": "gev",
        # "ensam": "xcvcxv",
        # "prodinra": "vxcv",
        # "publisher": "https://publisher.com/ID",
        # "link1": "https://link1.com/ID",
        # "link2": "https://link2.com/ID",
        # "link3": "https://link3.com/ID"
    }
    publisherlink = findURL(dataCrossRef["message"]["link"])
    if publisherlink:
        content["extref"]["publisher"] = publisherlink
    enKeywords = article.get("keyword", None)
    if not enKeywords:
        enKeywords = []
    content["keywords"] = {"en": enKeywords}

    content["codes"] = {
        # "classification": " ",
        # "acm": " ",
        # "mesh": " ",
        # "jel": " ",
        "halDomain": ["spi"]
    }
    if pdf_path:
        content["fileTmp"] = os.path.relpath(pdf_path, start=json_dir)
    content["authors"] = buildAuthors(dataScopus.authors)
    content["structures"] = buildAffiliations(content["authors"])
    content["license"] = "by"
    print("Built JSON for article: {}".format(article["title"]))
    # Serializing json
    json_object = json.dumps(content, indent=4)

    # Writing to sample.json
    json_file = os.path.join(json_dir, cleanFilename(doi) + ".json")
    with open(json_file, "w") as outfile:
        outfile.write(json_object)
    print("JSON file: {}".format(json_file))
    return json_file
