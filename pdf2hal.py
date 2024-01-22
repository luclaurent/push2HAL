#!/usr/bin/env python


####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Tools to upload PDF file on HAL based on title (read on the pdf file)
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### syntax: ./pdf2hal.py <pdf_file>
####*****************************************************************************************
####*****************************************************************************************


import sys,os,shutil
import json
import tempfile
import argparse
from pdftitle import get_title_from_file as titleFromPdf
import requests
from requests.auth import HTTPBasicAuth
# from sword2 import Connection
import logging
import fitz
from lxml import etree

FORMAT = 'PDF2HAL - %(asctime)s -  %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
Logger = logging.getLogger('pdf2hal')

DEFAULT_NB_CHAR=400
DEFAULT_CREDENTIALS_FILE='.apihal'
DEFAULT_UPLOAD_FILE_NAME_PDF='{}.pdf' #'upload.pdf'
DEFAULT_UPLOAD_FILE_NAME_XML='upload.xml'
DEFAULT_UPLOAD_FILE_NAME_ZIP='upload'
TXT_SEP='++++++++++++++++++++++'
DEFAULT_NAMESPACE_XML={'tei': 'http://www.tei-c.org/ns/1.0'}
ARCHIVES_API_URL = "https://api.archives-ouvertes.fr/search/"
ARCHIVES_TEI_URL = "https://api.archives-ouvertes.fr/oai/TEI/{hal_id}"
ARCHIVES_SWORD_API_URL = "https://api.archives-ouvertes.fr/sword/hal/" 
ARCHIVES_SWORD_PRE_API_URL = "https://api-preprod.archives-ouvertes.fr/sword/hal/"

def showPDFcontent(pdf_path, number=DEFAULT_NB_CHAR):
    try:
        doc = fitz.open(pdf_path)
        text = ""

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text += page.get_text()
            if len(text)>number:
                break

        # Display the first nb characters
        Logger.info('Content of file: {}'.format(pdf_path))
        Logger.info(TXT_SEP)
        for line in text[:number].split('\n'):
            Logger.info(line)
        Logger.info(TXT_SEP)
    except Exception as e:
        Logger.error(f"Error: {e}")

def load_credentials(args):
    cred = dict()
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
        if os.path.isfile(DEFAULT_CREDENTIALS_FILE):
            with open(DEFAULT_CREDENTIALS_FILE) as f:
                cred = json.load(f)
    
    return cred

def search_title_in_archives(pdf_title):
    Logger.debug(f"Searching for title: {pdf_title}")
    params = {
        'q': f'title_t:"{pdf_title}"',
        'fl': 'title_s,author_s,halId_s,label_s,docid',
        'wt': 'json',
        'rows': 5,  # Adjust the number of rows based on your preference
    }

    response = requests.get(ARCHIVES_API_URL, params=params)

    if response.status_code == 200:
        data = response.json().get('response', {}).get('docs', [])
        return data

    return []

def choose_from_results(results, forceSelection=False):
    Logger.info(TXT_SEP)
    Logger.info("Multiple results found:")
    for i, result in enumerate(results):
        Logger.info("[{}/{}]. {} - {}".format(i + 1,len(results),result.get('label_s', 'N/A'),result.get('halId_s', 'N/A')))

    Logger.info("Select a number to view details (0 to skip or m for manual definition): ")
    if forceSelection:
        choice = '1'
    else:
        choice = input(' > ')

    if choice.isdigit() and 0 <= int(choice) <= len(results):
        selected_result = results[int(choice) - 1]
        return selected_result
    elif choice == 'm':
        Logger.info('Provide title manually')
        manualTitle = input(' > ')
        return manualTitle
    else:
        Logger.warning("Invalid choice. Skipping.")

    return None

def download_tei_file(hal_id):
    Logger.debug(f"Downloading TEI file for halId: {hal_id}")
    params = {
        'q': f'halId_s:"{hal_id}"',
        'wt': 'xml-tei'
    }

    response = requests.get(ARCHIVES_API_URL, params=params)

    if response.status_code == 200:
        data = response.text
        #declare namespace
        key, value = list(DEFAULT_NAMESPACE_XML.items())[0]
        etree.register_namespace(key, value)
        return etree.fromstring(data.encode('utf-8'))

    return []

def writeXML(inTree,file_path):
    Logger.debug('Write XML file: {}'.format(file_path))
    et = etree.ElementTree(inTree)
    et.write(file_path)
        # f.write(etree.tostring(inTree, pretty_print=True, xml_declaration=True, encoding='utf-8'))

def cleanXML(inTree):
    # remove stamps
    for bad in inTree.findall(".//idno[@type='stamp']",inTree.nsmap):
        bad.getparent().remove(bad)


def addFileInXML(inTree,filePath,hal_id):
    newFilename = DEFAULT_UPLOAD_FILE_NAME_PDF.format(hal_id)
    Logger.debug('Copy original file to new one: {}->{}'.format(filePath,newFilename))
    shutil.copyfile(filePath,newFilename)
    # find section to add file
    inS = inTree.find('.//editionStmt',inTree.nsmap)
    if len(inS)==0:
        newE = etree.Element('editionStmt',nsmap=inTree.nsmap)
        pos= inTree.find('.//titleStmt',inTree.nsmap)
        pos.addnext(newE)
        inS = inTree.find('.//editionStmt',inTree.nsmap)
    # find subsection
    inSu = inS.find('.//edition',inTree.nsmap)
    if len(inSu)==0:
        inSu = etree.SubElement(inS,'edition',nsmap=inTree.nsmap)
        
    # check existing file
    # nFile = inS.xpath("//ref[@type='file']") #find('.//ref',inTree.nsmap)
    # add file
    nFile=etree.SubElement(inSu, "ref",nsmap=inTree.nsmap)
    nFile.set("type","file")
    nFile.set("subtype","author")
    nFile.set("n","1")
    nFile.set("target",newFilename)
    return newFilename

def buildZIP(xml_file_path,pdf_file_path):
    # create temporary directory
    tmp_dir_path=tempfile.mkdtemp()
    Logger.debug('Create temporary directory: {}'.format(tmp_dir_path))
    Logger.debug('Copy XML file: {}->{}'.format(xml_file_path,tmp_dir_path))
    shutil.copy(xml_file_path,tmp_dir_path)
    Logger.debug('Copy PDF file: {}->{}'.format(pdf_file_path,tmp_dir_path))
    shutil.copy(pdf_file_path,tmp_dir_path)
    # build zip archive
    archivePath = DEFAULT_UPLOAD_FILE_NAME_ZIP
    Logger.debug('Create zip archive: {}'.format(archivePath+'zip'))
    shutil.make_archive(archivePath, 'zip', tmp_dir_path)
    return archivePath+'.zip'

def preparePayload(tei_content,pdf_path,dirPath,hal_id):
    # clean XML
    cleanXML(tei_content)
    # declare new file as target in xml
    newPDF = addFileInXML(tei_content,pdf_path,hal_id)
    # write xml file
    xml_file_path = os.path.join(dirPath,DEFAULT_UPLOAD_FILE_NAME_XML)
    writeXML(tei_content,xml_file_path)
    # build zip file
    zipfile = buildZIP(xml_file_path,newPDF)
    #create header
    headers = {
        'Content-Type': 'application/zip',
        'Export-To-Arxiv': 'false',
        'Export-To-PMC': 'false',
        'Packaging': 'http://purl.org/net/sword-types/AOfr',
        'Content-Disposition': 'attachment; filename=' + xml_file_path,
        # 'Hide-For-RePEc': 'false',
        # 'Hide-In-OAI': 'false',
        # 'X-Allow-Completion': 'idext,grobid,affiliation'
        }
    return zipfile, headers

def upload2HAL(file,headers,credentials,server='preprod'):
    Logger.info('Upload to HAL')
    Logger.debug('File: {}'.format(file))
    Logger.debug('Headers: {}'.format(headers))
    
    if server=='preprod':
        url = ARCHIVES_SWORD_PRE_API_URL
    else:
        url = ARCHIVES_SWORD_API_URL
    
    Logger.debug('Upload via {}'.format(url))
    # read data to sent
    with open(file, 'rb') as f:
        data = f.read()
    #     res = requests.post(url=url,
    #                     data=data,
    
    res = requests.post(url=url,
                        # files={'upload.zip':file},
                        data=data,
                        headers=headers,
                        auth=HTTPBasicAuth(credentials['login'],credentials['passwd']))

    if res.status_code == 201:
        Logger.info("Successfully upload to HAL.")
    else:
        Logger.warning('Error: {}'.format(res.text))
        Logger.error("Failed to upload. Status code: {}".format(res.status_code))


def extract_info(pdf_path):
    Logger.debug('Extract title from PDF file')
    title = titleFromPdf(pdf_path)
    return title

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PDF2HAL - Upload PDF fil to HAL using title from the file.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('-c','--credentials', help='Path to the credentials file')
    parser.add_argument('-v','--verbose', help='Show all logs',action='store_true')
    parser.add_argument('-e','--prod', help='Execute on prod server',action='store_true')
    parser.add_argument('-l','--login', help='Username for API (HAL)')
    parser.add_argument('-p','--passwd', help='Password for API (HAL)')
    parser.add_argument('-f','--force', help='Force for no interaction',action='store_true')

    args = parser.parse_args()
    
    # activate verbose mode
    if args.verbose:
        Logger.setLevel(logging.DEBUG)
        
    Logger.info('Run PDF2HAL')
    Logger.info('')
    
    # activate production mode
    serverType='preprod'
    if args.prod:
        Logger.info('Execution mode: use production server (USE WITH CAUTION))')
        serverType='prod'
    else:
        Logger.info('Dryrun mode: use preprod server')
    
    
    #
    pdf_path = args.pdf_path
    Logger.debug('PDF file: {}'.format(pdf_path))
    dirPath = os.path.dirname(pdf_path)
    Logger.debug('Directory: {}'.format(dirPath))
    title = extract_info(pdf_path)
    
    # show first characters of pdf file
    showPDFcontent(pdf_path,number=DEFAULT_NB_CHAR)
    
    titleOk = False
    while not titleOk:
        if title:
            Logger.info(f'Title: {title}? (y/n)')
            choice = input(' > ')
            if choice == 'y':
                titleOk = True
        if not titleOk:
            Logger.info('Provide title manually')
            title = input(' > ')
        
    # Search for the PDF title in archives-ouvertes.fr
    selected_result = dict()
    while 'title_s' not in selected_result:
        archives_results = search_title_in_archives(title)

        if archives_results:
            selected_result = choose_from_results(archives_results,args.force)
            if 'title_s' not in selected_result:
                title = selected_result
        
    if selected_result:
        selected_title = selected_result.get('title_s', 'N/A')
        selected_author = selected_result.get('author_s', 'N/A')
        hal_id = selected_result.get('halId_s', None)

        Logger.info(f'Selected result in archives-ouvertes.fr:')
        Logger.info(f'Title: {selected_title}')
        Logger.info(f'Author: {selected_author}')
        Logger.info(f'HAL-id: {hal_id}')

        # Download TEI file
        tei_content = download_tei_file(hal_id)

        if len(tei_content)>0:
            # write TEI file            
            tei_file_path = os.path.join(dirPath,hal_id+".tei.xml")
            Logger.debug('Write TEI file: {}'.format(tei_file_path))
            writeXML(tei_content,tei_file_path)
            
            #prepare payload to upload to HAL
            file,payload=preparePayload(tei_content,pdf_path,dirPath,hal_id)
            
            # load credentials from file or from arguments
            credentials = load_credentials(args)
            
            # upload to HAL
            upload2HAL(file,payload,credentials,server=serverType)
        else:
            Logger.error("Failed to download TEI file.")
        
    else:
        print("No result selected.")

