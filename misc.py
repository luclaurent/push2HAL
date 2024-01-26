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
import curses
import time
import os
import json
import fitz
import default as dflt
from lxml import etree
from pdftitle import get_title_from_file as titleFromPdf

Logger = logging.getLogger('pdf2hal')

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
    """ Open and read pdf file and show first characters"""
    try:
        Logger.debug('Open and read PDF file: {}'.format(pdf_path))
        doc = fitz.open(pdf_path)
        text = ""

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text += page.get_text()
            if len(text)>number:
                break

        # Display the first nb characters
        Logger.info('Content of file: {}'.format(pdf_path))
        Logger.info(dflt.TXT_SEP)
        for line in text[:number].split('\n'):
            Logger.info(line)
        Logger.info(dflt.TXT_SEP)
    except Exception as e:
        Logger.error(f"Error: {e}")
        
def load_credentials(args):
    """ Load credentials from different sources"""
    cred = dict()
    # if args.hash:
    #     Logger.debug('Load credentials from hash')
    #     cred['hash']=args.hash
    if args.login and args.passwd:
        Logger.debug('Load credentials from arguments')
        cred['login']=args.login
        cred['passwd']=args.passwd
    elif args.credentials:
        Logger.debug('Load credentials from file {}'.format(args.credentials))
        if os.path.isfile(args.credentials):
            with open(args.credentials) as f:
                cred = json.load(f)
    else:
        Logger.debug('Load credentials from file')
        if os.path.isfile(dflt.DEFAULT_CREDENTIALS_FILE):
            with open(dflt.DEFAULT_CREDENTIALS_FILE) as f:
                cred = json.load(f)
                
    return cred

def checkTitle(title):
    """ Check if title is correct"""
    titleOk = False
    while not titleOk:
        if title:
            Logger.info(f'Title: {title}? ([y]/n)')
            choice = input(' > ')
            if choice == '':
                choice = 'y'
            if choice.lower() == 'y':
                titleOk = True
        if not titleOk:
            Logger.info('Provide title manually')
            title = input(' > ')
    return title

def writeXML(inTree,file_path):
    """ Write XML tree to file"""
    Logger.debug('Write XML file: {}'.format(file_path))
    et = etree.ElementTree(inTree)
    et.write(file_path)
        # f.write(etree.tostring(inTree, pretty_print=True, xml_declaration=True, encoding='utf-8'))

def cleanXML(inTree,xmlPath=None):
    """ Clean XML tree from given path"""
    # remove stamps
    if xmlPath:
        Logger.debug('Clean XML file: {}'.format(xmlPath))
        for bad in inTree.findall(xmlPath,inTree.nsmap):
            bad.getparent().remove(bad)
            
def extract_info(pdf_path):
    Logger.debug('Extract title from PDF file: {}'.format(pdf_path))
    title = titleFromPdf(pdf_path)
    return title

def adaptH(inStr):
    """ Adapt string to be used in header"""
    if inStr is None:
        return 'none'
    elif isinstance(inStr,bool):
        if inStr:
            return 'true'
        else:
            return 'false'
    else:
        return inStr