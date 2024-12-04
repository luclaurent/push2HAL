from push2HAL import libHAL as lib
from push2HAL import default as dflt
from push2HAL import execHAL
from lxml import etree
from pathlib import Path
import os

def test_updateXML():
    # load exisiting XML
    f = Path(__file__).parent / 'emse-01525674v3.tei.xml'
    tree = etree.parse(f)
    tree = tree.getroot()
    #
    # create data to update
    data ={
        "remove": [            
            "subtitle",
            "title",
            "authors"
        ],
        "update": [],
    "type": "article",
    "lang": "en",
    "title": {"en":"article", "fr":"article"},    
    "subtitle": "A subtitle",
    "abstract": {
        "en":"a very long abstract", 
        "fr": "un très long résumé"},
    "authors": [
        {
            "firstname": "John",
            "lastname": "Doe",
            "affiliation": "affiliation",
            "orcid": "orcid",
            "email": "email"
        },
        {
            "firstname": "Jane",
            "middle": "Middle",
            "lastname": "Doe",
            "affiliation": ["affiliationA", "affiliationB"],
            "orcid": "orcid",
            "email": "email"
        }        
    ],
    "licence": "cc-by",
    "notes":{
        "invited": "yes",
        "audience": "international",
        "popular": "no", 
        "peer": "yes", 
        "proceedings": "no", 
        "comment": "small comment",
        "description": "small description"
    },
    "ID":{
        "isbn": "978-1725183483",
        "journal": "Advanced Modeling and Simulation in Engineering Sciences",
        "issn": "xxx"
    },
    "infoDoc":
    {
        "publisher": "springer",
        "volume": "20",
        "issue": "1",
        "pages": "10-25",
        "serie": "a special collection",
        "datePub": "2024-01-01",
        "dateEPub": "2024-01"
    },
    "extref":{
        "bibcode": "erg",
        "ads": "gaergezg",
        "publisher": "https://publisher.com/ID",
        "link1": "https://link1.com/ID",
        "link2": "https://link2.com/ID",
        "link3": "https://link3.com/ID",
        "type": "append"
    },
    "keywords": {
        "en": ["keyword1", "keyword2"],
        "fr": ["mot-clé1", "mot-clé2"],
        "type": "replace"
    },
    "codes": {
        "halDomain": ["phys"],
        "type": "append"
    },
    "structures":[
        {
            "id": "affiliation",
            "name": "laboratory for MC, university of Yeah",
            "acronym": "LMC",
            "address": "Blue street 155, 552501 Olso, Norway",
            "url": "https://lmc.univ-yeah.com"
        },
        {
            "id": "affiliationB",
            "name": "laboratory for MCL, university of Yeah",
            "acronym": "LMCL",
            "address": {
                "line":"Blue street 155, 552501 Olso, Norway",
                "country":"Norway"
            },
            "url": "https://lmcl.univ-yeah.com"
        }
    ]
}
        
    # update XML
    lib.buildXML(data, tree)
    
def test_runUdpateHAL():
    res = execHAL.updateHAL(
        data={'abtract': 'ouioui'},
        pdf_path="examples/file.pdf",
        verbose=False,
        prod="preprod",
        credentials=None,
        completion=None,
        halid='emse-01525674',
        idhal=None,
    )
    assert res == os.EX_CONFIG