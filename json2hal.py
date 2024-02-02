from lxml import etree
import re
import os
import sys
import logging
import argparse
import json

import uploadHAL.libHAL as lib
import uploadHAL.misc as m
import uploadHAL.default as dflt

FORMAT = 'PDF2HAL - %(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
Logger = logging.getLogger('uploadHAL')



def run(args):
    """ execute using arguments"""
    exitStatus = os.EX_CONFIG
    # activate verbose mode
    if args.verbose:
        Logger.setLevel(logging.DEBUG)
        
    Logger.info('Run JSON2HAL')
    Logger.info('')
    
    # activate production mode
    serverType='preprod'
    if args.prod:
        Logger.info('Execution mode: use production server (USE WITH CAUTION))')
        serverType='prod'
    else:
        Logger.info('Dryrun mode: use preprod server')
    
    #
    json_path = args.json_path
    if os.path.isfile(json_path):        
        Logger.debug('JSON file: {}'.format(json_path))
        dirPath = os.path.dirname(json_path)
        Logger.debug('Directory: {}'.format(dirPath))
    else:
        exitStatus = os.EX_OSFILE
        return exitStatus
    
    # open and load json file
    f = open(json_path, 'r')
    # Reading from file
    dataJSON = json.loads(f.read())
    
    # build XML tree from json
    xmlData = lib.buildXML(dataJSON)
    # validate xml structure
    XMLstatus = lib.checkXML(xmlData)
    ET = etree.ElementTree(xmlData)
    ET.write('test.xml', pretty_print=True, xml_declaration=True, encoding='utf-8')
    
    
    if XMLstatus:
        Logger.debug('XML file is valid')
        # #prepare payload to upload to HAL
        # file,payload=lib.preparePayload(tei_content,pdf_path,dirPath,hal_id,options=options)
        
        # # load credentials from file or from arguments
        # credentials = m.load_credentials(args)
        
        # # upload to HAL
        # lib.upload2HAL(file,payload,credentials,server=serverType)
    else:
        Logger.error('XML file is not valid')
        exitStatus = os.EX_SOFTWARE
        # return exitStatus



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='JSON2HAL - Upload document metadata and optional PDF file to HAL using title from json file.')
    parser.add_argument('json_path', help='Path to the JSON file')
    parser.add_argument('-c','--credentials', help='Path to the credentials file')
    parser.add_argument('-v','--verbose', help='Show all logs',action='store_true')
    parser.add_argument('-e','--prod', help='Execute on prod server',action='store_true')
    parser.add_argument('-l','--login', help='Username for API (HAL)')
    parser.add_argument('-p','--passwd', help='Password for API (HAL)')
    parser.add_argument('-cc','--complete', help='Run completion (use grobid, idext or affiliation or list of theme spearated by comma)')
    parser.add_argument('-id','--idhal', help='Declare deposition on behalf of a specific idHAL')
    sys.argv = ['json2hal.py', 'test.json', '-v']#, '-a', 'hal-04215255']
    args = parser.parse_args()
    
    # run main function
    sys.exit(run(args))




