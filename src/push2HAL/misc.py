####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************


from loguru import logger as Logger
import curses
import time
import os
import re
import json
import fitz
from . import default as dflt
from lxml import etree
from pdftitle import get_title_from_file as titleFromPdf
from pdftitle import GetTitleParameters
import pycountry as pc

# specific formatting for loguru
_DEF_LOGURU_FORMAT_ = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> |"
    "<red>PUSH2HAL</red> |"
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> |"
    "- <level>{message}</level>"
)


def input_char(message):
    try:
        win = curses.initscr()
        win.addstr(0, 0, message)
        while True:
            ch = win.getch()
            if ch in range(32, 127):
                break
            time.sleep(0.05)
    finally:
        curses.endwin()
    return chr(ch)


def showPDFcontent(pdf_path, number=dflt.DEFAULT_NB_CHAR):
    """Open and read pdf file and show first characters"""
    try:
        Logger.debug("Open and read PDF file: {}".format(pdf_path))
        doc = fitz.open(pdf_path)
        text = ""

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text += page.get_text()
            if len(text) > number:
                break

        # Display the first nb characters
        Logger.info("Content of file: {}".format(pdf_path))
        Logger.info(dflt.TXT_SEP)
        for line in text[:number].split("\n"):
            Logger.info(line)
        Logger.info(dflt.TXT_SEP)
    except Exception as e:
        Logger.error(f"Error: {e}")


def load_credentials(args=None):
    """Load credentials from different sources"""
    cred = dict()
    # if args.hash:
    #     Logger.debug('Load credentials from hash')
    #     cred['hash']=args.hash
    # load input arguments depending on cases
    login = None
    passwd = None
    inputfile = None
    if args:
        if type(args) is dict:
            Logger.debug("Load credentials from dictionary")
            login = args.get("login",None)
            passwd = args.get("passwd",None)
            inputfile = args.get("file",None)
        elif type(args) is str():
            Logger.debug("Load credentials from string (file path)")
            inputfile = args
        elif type(args) is list():
            Logger.debug("Load credentials from list (login, passwd)")
            if len(args)>1:
                login = args[0]
                passwd = args[1]
        else:
            login = args.login
            passwd = args.passwd
            inputfile = args.credentials        
        
    if login and passwd:
        Logger.debug("Load credentials from arguments")
        cred["login"] = args.login
        cred["passwd"] = args.passwd
    elif inputfile:
        Logger.debug("Load credentials from file {}".format(inputfile))
        if os.path.isfile(inputfile):
            with open(inputfile) as f:
                cred = json.load(f)
    else:
        Logger.debug("Load credentials from root default file {}".format(dflt.DEFAULT_CREDENTIALS_FILE))
        if os.path.isfile(dflt.DEFAULT_CREDENTIALS_FILE):
            with open(dflt.DEFAULT_CREDENTIALS_FILE) as f:
                cred = json.load(f)
    if not cred:
        Logger.warning('No credentials found')

    return cred


def checkTitle(title):
    """Check if title is correct"""
    titleOk = False
    while not titleOk:
        if title:
            Logger.info(f"Title: {title}? ([y]/n)")
            choice = input(" > ")
            if choice == "":
                choice = "y"
            if choice.lower() == "y":
                titleOk = True
        if not titleOk:
            Logger.info("Provide title manually")
            title = input(" > ")
    return title


def checkXML(xml_tree, xsd_file_path=dflt.DEFAULT_VALIDATION_XSD, showError=True):
    """Validate XML file with XSD"""
    if not os.path.isfile(xsd_file_path):
        if os.path.isfile(os.path.join(os.path.dirname(__file__), xsd_file_path)):
            xsd_file_path = os.path.join(os.path.dirname(__file__), xsd_file_path)
    Logger.debug("Validate XML with {}".format(xsd_file_path))
    xmlschema_doc = etree.parse(xsd_file_path)
    xmlschema = etree.XMLSchema(xmlschema_doc)
    # run check
    status = xmlschema.validate(xml_tree)
    if not status:
        if showError:
            Logger.warning("XML file is not valid")
            for error in xmlschema.error_log:
                Logger.warning(error)
    return status

def writeXML(inTree, file_path, check=True):
    """Write XML tree to file"""
    Logger.debug("Write XML file: {}".format(file_path))
    et = inTree.getroottree()
    if check:
        checkXML(et)
    et.write(file_path, 
             pretty_print=True, 
             xml_declaration=True, 
             encoding='utf-8')
    # f.write(etree.tostring(inTree, pretty_print=True, xml_declaration=True, encoding='utf-8'))


def cleanXML(inTree, xmlPath=None):
    """Clean XML tree from given path"""
    # remove stamps
    if xmlPath:
        Logger.debug("Clean XML file: {}".format(xmlPath))
        for bad in inTree.findall(xmlPath, inTree.nsmap):
            bad.getparent().remove(bad)


def extract_info(pdf_path):
    Logger.debug("Extract title from PDF file: {}".format(pdf_path))
    try:
        params = GetTitleParameters()
        title = titleFromPdf(pdf_path,params)
    except Exception as e:
        Logger.error("Error: {}".format(e))
        Logger.error("Unable to get pdf title")
        title = None
    return title


def adaptH(inStr):
    """Adapt string to be used in header"""
    if inStr is None:
        return "none"
    elif isinstance(inStr, bool):
        if inStr:
            return "true"
        else:
            return "false"
    else:
        return inStr
    
def getCountryFromText(text):
    """ Try to get country from text """
    r = None
    if text:
        # with text
        for country in pc.countries:
            if country.name.lower() in text.lower():
                r = country.name
                break
        # with alpha3 code
        for country in pc.countries:
            if country.alpha_3.lower() in text.lower():
                r = country.name
                break
        # # with alpha2 code
        # for country in pc.countries:
        #     if country.alpha_2.lower() in text.lower():
        #         r = country.name
        #         break
    return r

def getAlpha2Country(text):
    """Try to get the alpha2 code of a country from a string"""
    r = None
    if text:
        try:
            r = pc.countries.search_fuzzy(text)
        except LookupError as e:
            Logger.error('LookupError: {}'.format(e))
            return None
    return r[0].alpha_2 if r else None

def checkISBN(isbn):
    """ Check if ISBN is OK """
    isbn = isbn.replace("-", "").replace(" ", "").upper();
    match = re.search(r'^(\d{9})(\d|X)$', isbn)
    if not match:
        return False

    digits = match.group(1)
    check_digit = 10 if match.group(2) == 'X' else int(match.group(2))

    result = sum((i + 1) * int(digit) for i, digit in enumerate(digits))
    return (result % 11) == check_digit

def showDict(dictIn):
    strOut = ''
    if type(dictIn) is dict:
        for k,v in dictIn.items():
            strOut = f'{k}: {v}\n'
    elif dictIn is None:
        strOut = 'None'
    return strOut    

def showList(listIn):
    strOut = ''
    if type(listIn) is list:
        for i in listIn:
            strOut = f'{i}\n'
    elif listIn is None:
        strOut = 'None'
    return strOut

def showItem(item):
    strOut = ''
    if item:
        if type(item) is dict:
            strOut = showDict(item)
        elif type(item) is list:
            strOut = showList(item)
        else:
            strOut = item
    elif item is None:
        strOut = 'None'
    else:
        strOut = item
    return strOut

def formatsolr(strIn):
    """ Format string based on Solr requirements 
        escape special characters: + - && || ! ( ) { } [ ] ^ " ~ * ? : \ """
    strOut = re.sub(r'([+\-&|!(){}[\]^"~*?:\\])', r'\\\1', strIn)
    return strOut