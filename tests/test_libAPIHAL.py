import os
import pytest
from push2HAL import libAPIHAL as lib
from push2HAL import default as dflt

def test_doiInHAL():
    api = lib.APIHAL()
    res = api.checkDoiInHAL('10.1007/s11831-017-9226-3')
    assert res == 'emse-01525674'
    
def test_doiNotInHAL():
    api = lib.APIHAL()
    res = api.checkDoiInHAL('10.1098/rsbm.1955.0005')
    assert res == None
    
    
@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_TYPES])
def test_exportTypeFromDOI(typeExport):
    api = lib.APIHAL()
    res = api.search(query={'doi':'10.1007/s11831-017-9226-3'},
                     returnFields=['doi','title','uri_s','producedDate_s','docType_s','authFullName_s'],
                     returnType=typeExport)
    assert res != None
    
@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_TYPES])
def test_exportTypeFromDOIbasic(typeExport):
    api = lib.APIHAL()
    res = api.basicSearch(txtsearch='10.1007/s11831-017-9226-3',
                          returnFields=['doi','title','uri_s','producedDate_s','docType_s','authFullName_s'],
                          returnType=typeExport)
    assert res != None
    
@pytest.mark.parametrize("typeExport", ["json","xml-tei"])
def test_exportTypeFromApproxTitle(typeExport):
    api = lib.APIHAL()
    res = api.getDataFromHAL(txtsearch='model',
                              typeI='title_approx',
                              typeDB="article",
                              typeR=typeExport)
    assert res != None
    
def test_getStructureData():
    api = lib.APIHAL()
    res = api.getDataFromHAL(txtsearch='LMSSC',
                             typeDB="structure")
    assert res != None