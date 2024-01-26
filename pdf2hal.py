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

FORMAT = 'PDF2HAL - %(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
Logger = logging.getLogger('pdf2hal')


def run(args):
    """ execute using arguments"""



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
    sys.argv = ['pdf2hal.py', 'allix1989.pdf', '-f', '-v']
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

