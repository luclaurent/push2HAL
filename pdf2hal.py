#!/usr/bin/env python


####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Tools to upload PDF file on HAL based on title (read on the pdf file)
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### syntax: ./pdf2hal.py <pdf_file>
####
#### description available on https://github.com/luclaurent/uploadHAL
####*****************************************************************************************
####*****************************************************************************************


import sys,os
import argparse
import logging

import libHAL as lib
import misc as m
import default as dflt

FORMAT = 'PDF2HAL - %(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
Logger = logging.getLogger('pdf2hal')


def run(args):
    """ execute using arguments"""
    exitStatus = os.EX_CONFIG
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
    if os.path.isfile(pdf_path):        
        Logger.debug('PDF file: {}'.format(pdf_path))
        dirPath = os.path.dirname(pdf_path)
        Logger.debug('Directory: {}'.format(dirPath))
        title = m.extract_info(pdf_path)
    else:
        exitStatus = os.EX_OSFILE
        return exitStatus
    
    # show first characters of pdf file
    m.showPDFcontent(pdf_path,number=dflt.DEFAULT_NB_CHAR)
    
    # check title and/or provide new one
    if not args.halid:
        if not args.force:
            title = m.checkTitle(title)
        else:
            Logger.info('Force mode: use title \'{}\''.format(title))
        
        # Search for the PDF title in HAL.science
        selected_result = dict()
        while 'title_s' not in selected_result:
            archives_results = lib.getDataFromHAL(title=title)

            if archives_results:
                selected_result = lib.choose_from_results(archives_results,args.force)
                if 'title_s' not in selected_result:
                    title = selected_result
            else:
                Logger.error('No result found in HAL.science')
                exitStatus = os.EX_NOTFOUND
                return exitStatus
            
        if selected_result:
            selected_title = selected_result.get('title_s', 'N/A')
            selected_author = selected_result.get('author_s', 'N/A')
            hal_id = selected_result.get('halId_s', None)

            Logger.info('Selected result in archives-ouvertes.fr:')
            Logger.info('Title: {}'.format(selected_title))
            Logger.info('Author: {}'.format(selected_author))
            Logger.info('HAL-id: {}'.format(hal_id))
    else:
        Logger.info('Provided HAL_id: {}'.format(args.halid))
        hal_id = args.halid
        # get data from HAL
        dataHAL = lib.getDataFromHAL(DOCid=hal_id)
        if len(dataHAL)>0:
            selected_title = dataHAL[0].get('title_s', 'N/A')
            selected_author = dataHAL[0].get('author_s', 'N/A')
            hal_id = dataHAL[0].get('halId_s', None)
            
            Logger.info('Title: {}'.format(selected_title))
            Logger.info('Author: {}'.format(selected_author))
            Logger.info('HAL-id: {}'.format(hal_id))
        else:
            Logger.error("Document's ID {} not found in HAL".format(hal_id))
            exitStatus = os.EX_SOFTWARE
            return exitStatus

    if hal_id:
        # Download TEI file
        tei_content = lib.getDataFromHAL(DOCid=hal_id, typeR='xml-tei')

        if len(tei_content)>0:
            # write TEI file            
            tei_file_path = os.path.join(dirPath,hal_id+".tei.xml")
            Logger.debug('Write TEI file: {}'.format(tei_file_path))
            m.writeXML(tei_content,tei_file_path)
            
            #prepare payload to upload to HAL
            file,payload=lib.preparePayload(tei_content,pdf_path,dirPath,hal_id)
            
            # load credentials from file or from arguments
            credentials = m.load_credentials(args)
            
            # upload to HAL
            lib.upload2HAL(file,payload,credentials,server=serverType)
        else:
            Logger.error("Failed to download TEI file.")
            exitStatus = os.EX_SOFTWARE
            return exitStatus
        
    else:
        Logger.error("No result selected.")
        exitStatus = os.EX_SOFTWARE
        return exitStatus
    
    return exitStatus


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PDF2HAL - Upload PDF file to HAL using title from the file.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('-a','--halid', help='HALid of document to update')
    parser.add_argument('-c','--credentials', help='Path to the credentials file')
    parser.add_argument('-v','--verbose', help='Show all logs',action='store_true')
    parser.add_argument('-e','--prod', help='Execute on prod server',action='store_true')
    parser.add_argument('-l','--login', help='Username for API (HAL)')
    parser.add_argument('-p','--passwd', help='Password for API (HAL)')
    parser.add_argument('-f','--force', help='Force for no interaction',action='store_true')
    sys.argv = ['pdf2hal.py', 'allix1989.pdf', '-v']#, '-a', 'hal-04215255']
    args = parser.parse_args()
    
    # run main function
    sys.exit(run(args))
