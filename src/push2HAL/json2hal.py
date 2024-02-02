#!/usr/bin/env python

####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Tools to create note in HAL repo from JSON file w/- or w/o PDF file
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### syntax: json2hal.py <json_file>
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************


import sys
import argparse
import logging
from . import execHAL
from . import misc as m

FORMAT = "JSON2HAL - %(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
Logger = logging.getLogger("push2HAL")


def start():
    parser = argparse.ArgumentParser(description='JSON2HAL - Upload document metadata and optional PDF file to HAL using data from json file.')
    parser.add_argument('json_path', help='Path to the JSON file')
    parser.add_argument('-c','--credentials', help='Path to the credentials file')
    parser.add_argument('-v','--verbose', help='Show all logs',action='store_true')
    parser.add_argument('-e','--prod', help='Execute on prod server',action='store_true')
    parser.add_argument('-t','--test', help='Execute on prod server but with test mode (dry-run)',action='store_true')
    parser.add_argument('-l','--login', help='Username for API (HAL)')
    parser.add_argument('-p','--passwd', help='Password for API (HAL)')
    parser.add_argument('-cc','--complete', help='Run completion (use grobid, idext or affiliation or list of theme spearated by comma)')
    parser.add_argument('-id','--idhal', help='Declare deposition on behalf of a specific idHAL')
    sys.argv = ['json2hal.py', 'test.json', '-v', '-t']#, '-a', 'hal-04215255']
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
    sys.exit(execHAL.runJSON2HAL(args.json_path,
                                 verbose=args.verbose,
                                 prod=prodmode,
                                 credentials=credentials,
                                 completion=args.complete,
                                 idhal=args.idhal))


if __name__ == "__main__":
    start()




