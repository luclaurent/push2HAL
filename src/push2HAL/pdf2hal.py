#!/usr/bin/env python


####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Tools to upload PDF file on HAL based on title (read on the pdf file)
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### syntax: pdf2hal.py <pdf_file>
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************


import sys
import argparse
import logging
from . import execHAL
from . import misc as m

FORMAT = 'PDF2HAL - %(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
Logger = logging.getLogger('push2HAL')



def start():
    parser = argparse.ArgumentParser(description='PDF2HAL - Upload PDF file to HAL using title from the file.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('-a','--halid', help='HALid of document to update')
    parser.add_argument('-c','--credentials', help='Path to the credentials file')
    parser.add_argument('-v','--verbose', help='Show all logs',action='store_true')
    parser.add_argument('-e','--prod', help='Execute on prod server',action='store_true')
    parser.add_argument('-t','--test', help='Execute on prod server but with test mode (dry-run)',action='store_true')
    parser.add_argument('-l','--login', help='Username for API (HAL)')
    parser.add_argument('-p','--passwd', help='Password for API (HAL)')
    parser.add_argument('-f','--force', help='Force for no interaction',action='store_true')
    parser.add_argument('-cc','--complete', help='Run completion (use grobid, idext or affiliation or list of theme spearated by comma)')
    parser.add_argument('-id','--idhal', help='Declare deposition on behalf of a specific idHAL')
    # sys.argv = ['pdf2hal.py', 'allix1989.pdf', '-v']#, '-a', 'hal-04215255']
    args = parser.parse_args()
    
    # load credentials from file or from arguments
    credentials = m.load_credentials(args)
    
    # adapt mode:
    prodmode = 'preprod'
    if args.prod:
        prodmode = 'prod'
    if args.test:
        prodmode = 'test'
    
    # run main function
    sys.exit(execHAL.runPDF2HAL(args.pdf_path,
                                 verbose=args.verbose,
                                 prod=prodmode,
                                 credentials=credentials,
                                 completion=args.complete,
                                 halid=args.halid,
                                 idhal=args.idhal,
                                 interaction=not args.force))


if __name__ == "__main__":
    start()
