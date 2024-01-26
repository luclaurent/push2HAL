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

import default as dflt
import misc as m

Logger = logging.getLogger('pdf2hal')


def search_title_in_archives(pdf_title):
    """Search for a title in HAL archives"""
    Logger.debug(f"Searching for title: {pdf_title}")
    params = {
        'q': f'title_t:"{pdf_title}"',
        'fl': 'title_s,author_s,halId_s,label_s,docid',
        'wt': 'json',
        'rows': 5,  # Adjust the number of rows based on your preference
    }
    # request and get response
    response = requests.get(dflt.ARCHIVES_API_URL, params=params)

    if response.status_code == 200:
        data = response.json().get('response', {}).get('docs', [])
        return data

    return []


def choose_from_results(results, forceSelection=False, 
                        maxNumber=dflt.DEFAULT_MAX_NUMBER_RESULTS):
    """ Select result from a list of results"""
    Logger.info(dflt.TXT_SEP)
    Logger.info("Multiple results found:")
    for i, result in enumerate(results):
        # print only the first maxNumber results
        if i < maxNumber:
            Logger.info("[{}/{}]. {} - {}".format(i + 1,len(results),result.get('label_s', 'N/A'),result.get('halId_s', 'N/A')))
        else:
            break

    Logger.info("Select a number to view details (0 to skip or m for manual definition): ")
    
    choiceOK = False
    while not choiceOK:
        if forceSelection:
            choice = '1'
            choiceOK = True
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
            Logger.warning("Invalid choice.")

    return None

def download_tei_file(hal_id):
    """ Download TEI-XML file from HAL"""
    Logger.debug(f"Downloading TEI file for halId: {hal_id}")
    params = {
        'q': f'halId_s:"{hal_id}"',
        'wt': 'xml-tei'
    }
    # request and get response
    response = requests.get(dflt.ARCHIVES_API_URL, params=params)

    if response.status_code == 200:
        data = response.text
        #declare namespace
        key, value = list(dflt.DEFAULT_NAMESPACE_XML.items())[0]
        etree.register_namespace(key, value)
        return etree.fromstring(data.encode('utf-8'))

    return []


def addFileInXML(inTree,filePath,hal_id):
    """ Add new imported file in XML"""
    newFilename = dflt.DEFAULT_UPLOAD_FILE_NAME_PDF.format(hal_id)
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
    Logger.debug('Add file in XML: {}'.format(newFilename))
    nFile=etree.SubElement(inSu, "ref",nsmap=inTree.nsmap)
    nFile.set("type","file")
    nFile.set("subtype","author")
    nFile.set("n","1")
    nFile.set("target",newFilename)
    return newFilename

def buildZIP(xml_file_path,pdf_file_path):
    """ Build ZIP archive for HAL deposit (containing XML and PDF)"""
    # create temporary directory
    tmp_dir_path=tempfile.mkdtemp()
    Logger.debug('Create temporary directory: {}'.format(tmp_dir_path))
    Logger.debug('Copy XML file: {}->{}'.format(xml_file_path,tmp_dir_path))
    shutil.copy(xml_file_path,tmp_dir_path)
    Logger.debug('Copy PDF file: {}->{}'.format(pdf_file_path,tmp_dir_path))
    shutil.copy(pdf_file_path,tmp_dir_path)
    # build zip archive
    archivePath = dflt.DEFAULT_UPLOAD_FILE_NAME_ZIP
    Logger.debug('Create zip archive: {}'.format(archivePath+'zip'))
    shutil.make_archive(archivePath, 'zip', tmp_dir_path)
    return archivePath+'.zip'


def preparePayload(tei_content,
                   pdf_path=None,
                   dirPath=None,
                   hal_id=None,
                   options=dict()):
    """ Prepare payload for HAL deposit """
    # clean XML
    if pdf_path:
        m.cleanXML(tei_content,".//idno[@type='stamp']")
        # declare new file as target in xml
        newPDF = addFileInXML(tei_content,pdf_path,hal_id)
    # write xml file
    xml_file_path = os.path.join(dirPath,dflt.DEFAULT_UPLOAD_FILE_NAME_XML)
    m.writeXML(tei_content,xml_file_path)
    # build zip file
    if pdf_path:
        zipfile = buildZIP(xml_file_path,newPDF)
    #create header
    header = dict()
    # default:
    header['Content-Disposition'] = None
    header['On-Behalf-Of'] = options.get('idFrom',None)
    header['Export-To-Arxiv'] = False
    header['Export-To-PMC'] = False
    header['Hide-For-RePEc'] = False
    header['Hide-In-OAI'] = False
    header['X-Allow-Completion'] = options.get('allowCompletion',False)
    header['Packaging'] = options.get('allowCompletion',dflt.DEFAULT_XML_SWORD_PACKAGING)
    if pdf_path:
        header['Content-Type'] = 'application/zip'
        header['Export-To-Arxiv'] = options.get('export2arxiv',header['Export-To-Arxiv'])
        header['Export-To-PMC'] = options.get('export2pmc',header['Export-To-PMC'])
        header['Hide-For-RePEc'] = options.get('hide4repec',header['Hide-For-RePEc'])
        header['Hide-In-OAI'] = options.get('hide4oai',header['Hide-In-OAI'])
        header['Content-Disposition']= 'attachment; filename="{}"'.format(xml_file_path)
    else:
        header['Content-Type'] = 'text/xml'
    
    return zipfile, header


def upload2HAL(file,
                headers,
                credentials,
                server='preprod'):
    """ Upload to HAL """
    Logger.info('Upload to HAL')
    Logger.debug('File: {}'.format(file))
    Logger.debug('Headers: {}'.format(headers))
    
    if server=='preprod':
        url = dflt.ARCHIVES_SWORD_PRE_API_URL
    else:
        url = dflt.ARCHIVES_SWORD_API_URL
    
    Logger.debug('Upload via {}'.format(url))
    # read data to sent
    with open(file, 'rb') as f:
        data = f.read()
    
    res = requests.post(url=url,
                        data=data,
                        headers=headers,
                        auth=HTTPBasicAuth(credentials['login'],credentials['passwd']))

    if res.status_code == 201:
        Logger.info("Successfully upload to HAL.")
    else:
        #read error message
        xmlResponse = etree.fromstring(res.text.encode('utf-8'))
        elem = xmlResponse.findall(dflt.DEFAULT_ERROR_DESCRIPTION_SWORD_LOC,xmlResponse.nsmap)
        Logger.error("Failed to upload. Status code: {}".format(res.status_code))
        if len(elem)>0:
            for i in elem:
                Logger.warning('Error: {}'.format(i.text))