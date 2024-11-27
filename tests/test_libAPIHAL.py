import pytest
import tempfile
import os
import contextlib as ctl
from pathlib import Path
from push2HAL import libAPIHAL as lib
from push2HAL import default as dflt

listDirectAccessFormat = list(dflt.HAL_DIRECT_ACCESS_FORMATS.values())


def test_doiInHAL():
    res = lib.checkDoiInHAL('10.1007/s11831-017-9226-3')
    assert res == 'emse-01525674'
    
def test_doiNotInHAL():
    res = lib.checkDoiInHAL('10.1098/rsbm.1955.0005')
    assert res == None
    
@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOC])
def test_exportTypeFromDOI(typeExport):
    api = lib.APIHAL()
    res = api.search(query={'doi':'10.1007/s11831-017-9226-3'},
                     returnFields=['doi','title','uri_s','producedDate_s','docType_s','authFullName_s'],
                     returnFormat=typeExport)
    assert res is not None
    
@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOC])
def test_exportTypeFromDOIbasic(typeExport):
    api = lib.APIHAL()
    res = api.basicSearch(txtsearch='10.1007/s11831-017-9226-3',
                          returnFields=['doi','title','uri_s','producedDate_s','docType_s','authFullName_s'],
                          returnFormat=typeExport)
    assert res is not None
    
@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOC])
def test_exportTypeFromApproxTitle(typeExport):
    api = lib.APIHAL()
    res = api.basicSearch(txtsearch='model',
                          returnFields=['doi','title','uri_s','producedDate_s','docType_s','authFullName_s'],
                          returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", ["json"])
def test_exportFromCollection(typeExport):
    api = lib.APIHAL()
    res = api.basicSearch(txtsearch='model',
                          returnFields=['doc_idhal'],
                          returnFormat=typeExport,
                          collection="CSMA2024")
    assert res is not None

@pytest.mark.parametrize("typeExport", ["json"])
def test_exportEverythingFromCollection(typeExport):
    api = lib.APIHAL()
    res = api.basicSearch(#txtsearch='',
                          #returnFields=['doc_idhal'],
                          #returnFormat=typeExport,
                          collection="CSMA2024")
    assert res is not None

@pytest.mark.parametrize("typeExport", ["json"])
def test_exportExactFromCollection(typeExport):
    api = lib.APIHAL()
    res = api.search(query={'title':'MANTA: an industrial-strength open-source high performance explicit and implicit multi-physics solver'},
                          returnFields=['doc_idhal'],
                          returnFormat=typeExport,
                          collection="CSMA2024")
    assert res[0].get('halId_s') == "hal-04610968"

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_AUTHOR])
def test_exportAuthor(typeExport):
    api = lib.APIHALauthor()
    res = api.basicSearch(txtsearch='Laurent',
                            returnFields=['authFullName_s','authIdHal_i','authIdRef_s','authIdArxiv_s','authIdOrcid_s'],
                            returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_AUTHORSTRUCTURE])
def test_exportAuthorStructure(typeExport):
    api = lib.APIHALauthorstructure()
    res = api.search(query={"last_name":'Laurent',"first_name":"Luc"},
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_ANR])
def test_exportANR(typeExport):
    api = lib.APIHALanr()
    res = api.basicSearch(txtsearch="optimisation",
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_EUROPEANPROJECT])
def test_exportEuroProject(typeExport):
    api = lib.APIHALeuropeanproject()
    res = api.basicSearch(txtsearch="optimisation",
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOCTYPE])
def test_exportDocType(typeExport):
    api = lib.APIHALdoctype()
    res = api.basicSearch(txtsearch="inria",
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOMAIN])
def test_exportDomain(typeExport):
    api = lib.APIHALdomain()
    res = api.basicSearch(txtsearch="optimisation",
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_INSTANCE])
def test_exportInstance(typeExport):
    api = lib.APIHALinstance()
    res = api.basicSearch(returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_JOURNAL])
def test_exportJournal(typeExport):
    api = lib.APIHALjournal()
    res = api.basicSearch(txtsearch="optimisation",
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_METADATA])
def test_exportMetaData(typeExport):
    api = lib.APIHALmetadata()
    res = api.search(query={"instance_name_exact":"inria"},
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_METADATALIST])
def test_exportMetaDataList(typeExport):
    api = lib.APIHALmetadatalist()
    res = api.basicSearch(txtsearch="optimisation",
                    returnFields=[],
                    returnFormat=typeExport)
    assert res is not None

@pytest.mark.parametrize("typeExport", [None,*dflt.HAL_API_ALLOWED_RETURN_FORMATS_STRUCTURE])
def test_exportStructure(typeExport):
    api = lib.APIHALstructure()
    res = api.basicSearch(txtsearch="LMSSC",
                    returnFields=[],
                    returnFormat=typeExport)
    # depending of export format
    valueOk = 12568
    if api.returnFormat == "json":
        assert res[0].get("docid") == str(valueOk)
    elif api.returnFormat == "csv":
        assert int(res.loc[0].at['docid']) == valueOk
    elif api.returnFormat == "xml":
        assert res.xpath('//str[@name="docid"]')[0].text == str(valueOk)
    elif api.returnFormat == "xml-tei":
        structId = res.xpath('//org')[0].attrib.get('{}id'.format(dflt.DEFAULT_XML_LANG))
        assert structId == '{}-{}'.format('struct',valueOk)
    else:
        assert False

@pytest.mark.parametrize("typeExport", 
                         [None,*dflt.HAL_DIRECT_ACCESS_FORMATS_LIST])
@pytest.mark.parametrize("fileExport",[None, "test_export"])
@pytest.mark.parametrize("halid",["emse-01525674", "hal-03690766"])
def test_directAccess(typeExport,fileExport,halid):
    
    ## depending on raising exception or not
    expectation = ctl.nullcontext()
    if halid=="hal-03690766" and typeExport=="document":
        expectation = pytest.raises(Exception)
    
    if fileExport:
        dirtmp = tempfile.mkdtemp()
        fileExport = Path(dirtmp) / fileExport
    with expectation as excinfo:
        da = lib.directAccess(hal_id=halid,
                            type=typeExport,
                            file=fileExport)
    final_satus = False
    if excinfo:
        if excinfo.value.args[0].startswith('Error on url request'):
            if halid=="hal-03690766" and typeExport=="document":
                final_satus = True
    else:
        if da.data is not None:
            if da.file is not None:
                if da.file.exists():
                    if os.path.getsize(da.file) > 0:
                        final_satus = True
            else:
                final_satus = True
    assert final_satus
