####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************


from loguru import logger
import os,sys
from abc import ABC
from furl import furl
import doi as doilib
import requests
from lxml import etree
import bibtexparser as btexp
from io import StringIO
import pandas as pd
import feedparser

from . import default as dflt
from . import misc as m

## create a custom logger
logger.remove()
logger.add(sys.stderr, format=m._DEF_LOGURU_FORMAT_)

## st XML's namespace for everything
TEI = "{}".format(dflt.DEFAULT_TEI_URL_NAMESPACE)



class APIHALbase(ABC):
    """ Base class for APIHAL """
    def __init__(self):
        self.url = furl(dflt.HAL_API_URL['base'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE
        self.defaultReturnFields = [] ## default value(s) provided by HAL API
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT
        self.collection = None
        self.query = None
        self.returnFields = None
        self.returnFormat = None
        self.lastResponse = None
        self.lastParams = None
        self.indexElements = [-1]
        self.nbElements = 0
        self.maxResults = dflt.DEFAULT_MAX_NUMBER_RESULTS
        
    def showConfig(self):
        """ Show the configuration of the current HAL API """
        logger.info("{}".format("="*len(str(self))))
        logger.info("{}".format(self))
        logger.info("{}".format("="*len(str(self))))
        logger.info('Current configuration')
        logger.info(' + URL: {}'.format(self.getBaseUrl()))
        logger.info(' + Defined query: {}'.format(m.showItem(self.query)))
        logger.info(' + Defined return fields: {}'.format(m.showItem(self.returnFields)))
        logger.info(' + Defined return type: {}'.format(self.returnFormat))
        logger.info("{}".format("="*len(str(self))))
        logger.info('Last request')
        logger.info(' + Last Response: {}'.format(self.lastResponse)) 
        logger.info(' + Last Params: {}'.format(m.showItem(self.lastParams)))
        logger.info("{}".format("="*len(str(self))))
        logger.info('Allowed items')
        logger.info(' + Allowed return types: {}'.format(self.ALLOWED_RETURN_FORMATS))
        logger.info(' + Allowed query types: {}'.format(self.ALLOWED_QUERY_TYPES))
        logger.info(' + Allowed return fields: {}'.format(self.ALLOWED_RETURN_FIELDS))
        pass
    
    def __repr__(self) -> str:
        return "HAL API base class"   
     
    def __str__(self) -> str:
        return "HAL API base class"
    
    def setCollection(self, collection=None):
        """ Set the collection to search in (works only for base HAL API """
        self.collection = collection
    
    def setNbResults(self, nbResults=-1):
        """ Set the number of results to return """
        if type(nbResults) is int:
            self.indexElements = [nbResults]
            if nbResults > 10000:
                logger.warning("Number of results too high, set to 10000")
                self.indexElements = [10000]
        if type(nbResults) is list:
            if len(nbResults) == 2:
                if nbResults[0] >= 0 and nbResults[1] > nbResults[0]:
                    self.indexElements = nbResults
                elif nbResults[0] == nbResults[1]:
                    self.indexElements = [nbResults[0]]
                elif nbResults[1] > 10000:
                    logger.warning("Number of results too high, set to 10000")
                    self.indexElements = [nbResults[0],10000]
            if len(nbResults) == 1:
                self.indexElements = nbResults
                if nbResults[0] > 10000:
                    logger.warning("Number of results too high, set to 10000")
                    self.indexElements = [10000]
    
    def setReturnFormat(self, typeR="json"):
        """ Set the return type of the HAL API """
        if typeR in self.ALLOWED_RETURN_FORMATS:
            logger.debug('Return typeset : {}'.format(typeR))
            self.returnFormat = typeR                
        else:            
            logger.warning("Unknown return type: {} for {}".format(typeR,self))
            logger.warning("Force to use {}".format(self.defaultReturnFormat))
            self.returnFormat = self.defaultReturnFormat
            
    def setReturnFields(self, returnFields=None, append = False):
        """ Set the return fields of the HAL API """
        if type(returnFields) is str:
            returnFields = returnFields.split(",")
            if type(returnFields) is not list:
                returnFields = [returnFields]
                
        returnFieldsFormat = list()        
        if returnFields is None or len(returnFields) == 0:
            returnFields = list(self.ALLOWED_RETURN_FIELDS.values())
            logger.warning("No return fields set, return all fields")
        else:
            for item in returnFields:
                if item not in self.ALLOWED_RETURN_FIELDS \
                    and item not in list(self.ALLOWED_RETURN_FIELDS.values()):
                    logger.warning("Unknown return field: {} for {}".format(item,self))
                    returnFields.remove(item)
                elif item in self.ALLOWED_RETURN_FIELDS:
                    returnFieldsFormat.append(self.ALLOWED_RETURN_FIELDS[item])
                elif item in list(self.ALLOWED_RETURN_FIELDS.values()):
                    returnFieldsFormat.append(item)
        if append:
            if self.returnFields is None:
                self.returnFields = []
            self.returnFields.extend(returnFieldsFormat)
        else:
            self.returnFields = returnFieldsFormat
            
    
    def setQuery(self, query=None):
        """ Check and set the appropriate syntax for query of HAL API """
        if query is None:
            logger.warning("No provided query")
            pass
        elif type(query) is dict:
            if len(query) == 0:
                logger.warning("Empty query")
                pass 
            else:
                checkedQuery = dict()
                for k,v in query.items():
                    if k in list(self.ALLOWED_QUERY_TYPES.keys()):
                        checkedQuery[self.ALLOWED_QUERY_TYPES[k]] = v
                    elif k in list(self.ALLOWED_QUERY_TYPES.values()):
                        checkedQuery[k] = v
                    else:
                        logger.warning("Unknown query: {} for {}".format(k,self))
                if len(query) == 0:
                    logger.warning("Empty checked queries")
                    pass 
                self.query = checkedQuery


            
    def formatData(self, response):
        """ Format response depending on return type """
        if response.status_code == 200:
            if self.getReturnFormat() == "json":
                data = response.json().get("response", {}).get("docs", [])
                if not data:
                    data = response.json().get("response", {}).get("result", [])
            elif self.getReturnFormat() == "xml-tei" \
                    or self.getReturnFormat() == "xml" \
                    or self.getReturnFormat() == "atom":
                dataTmp = response.text
                # declare namespace
                # key, value = list(dflt.DEFAULT_NAMESPACE_XML.items())[0]
                # etree.register_namespace(key, value)
                data = etree.fromstring(dataTmp.encode("utf-8"))
            elif self.getReturnFormat() == "bibtex":
                data = btexp.parse_string(response.text)
            elif self.getReturnFormat() == "csv":
                data = pd.read_csv(StringIO(response.text))
            elif self.getReturnFormat() == "endnote":
                data = response.text
            elif self.getReturnFormat() == "rss":
                data = feedparser.parse(response.text)
        else:
            data = []
        return data
    
    def mergeData(self, data):
        """ Merge data from multiple requests """
        if self.getReturnFormat() == "json" \
                or self.getReturnFormat() == "endnote":
            dataOut = []
            for d in data:
                dataOut.extend(d)
        elif self.getReturnFormat() == "rss":
            dataOut = None
            # merge all rss data
            for d in data:
                if dataOut is None:
                    dataOut = d
                else:
                    dataOut.entries.extend(d.entries)
        elif self.getReturnFormat() == "bibtex":
            # merge all bibtex data using bibtexparser
            dataOut = None
            for d in data:
                if dataOut is None:
                    dataOut = d
                else:
                    dataOut.add(d.entries)
        elif self.getReturnFormat() == "csv":
            # merge all csv data using pandas
            dataOut = pd.concat(data)
        elif self.getReturnFormat() == "xml-tei" \
                or self.getReturnFormat() == "xml" \
                or self.getReturnFormat() == "atom":
            # merge all xml data using etree
            dataOut = None
            for d in data:
                if dataOut is None:
                    dataOut = d
                else:
                    dataOut.extend(d)
        else:
            pass
        return dataOut

        
    def getReturnFields(self):
        return ','.join(self.returnFields)
    
    def getReturnFormat(self):
        if self.returnFormat is None:
            logger.warning('No return type set, return {}'.format(self.defaultReturnFormat))
            return self.defaultReturnFormat
        else:
            return self.returnFormat
        
    def getBaseQuery(self):
        baseQueryList = []
        if type(self.query) is dict:
            for key, value in self.query.items():
                baseQueryList.append("{}:{}".format(key, value))
        return ",".join(baseQueryList)
        
    def getParams(self):
        """ Get the parameters for the URL request for the HAL API request """
        params = {}
        # get query
        query = self.getBaseQuery()
        if query:
            params["q"] = query
        # get return type
        typeR = self.getReturnFormat()
        if typeR:
            params["wt"] = typeR
        # get return fields
        returnFields = self.getReturnFields()
        if returnFields:
            params["fl"] = returnFields
        # get elements number
        indexElements = self.indexElements
        if len(indexElements) == 2:
            params["start"] = max(0,indexElements[0])
            params["rows"] = indexElements[1]
        elif len(indexElements) == 1 and indexElements[0] > 0:
            params["rows"] = indexElements

        return params
    
    def getBaseUrl(self):
        return self.url.url

    def getNbResults(self, params=None):
        """ Get the number of results for a query """
        # adapt query to force json format and return nothing except the number of results
        paramsCopy = params.copy()
        paramsCopy["wt"] = "json"
        paramsCopy["rows"] = 0
        # execute request
        data = self.getUrlRequest(paramsCopy, raw=True)
        # get number of results
        self.nbElements = data.json().get("response", {}).get("numFound", [])
        return self.nbElements
        
    def getUrlRequest(self, params=None, raw=False):
        """ Make the request to the HAL API """
        if not params:
            params = self.getParams()
        response = requests.get(self.getBaseUrl(), params=params)
        #
        self.lastResponse = response
        self.lastParams = params
        #
        responseChecked = AnalyseResponse(response)
        if not responseChecked.ok:
            logger.error('Error on url request: {}'.format(responseChecked.message))
            raise Exception('Error on url request: {}'.format(responseChecked.message))
        if raw:
            return response
        else:
            return self.formatData(response)

    def getAllResults(self,params=None):
        """ Get all results for a query """
        if not params:
            params = self.getParams()
        # get number of results
        nbResults = self.getNbResults(params)
        logger.debug("Number of results: {}".format(nbResults))
        # get all results
        rows = 0
        allResultsRaw = []
        while rows < self.maxResults:
            params["start"] = rows
            params["rows"] = self.maxResults
            allResultsRaw.append(self.getUrlRequest(params))
            rows += self.maxResults
        return self.mergeData(allResultsRaw)

    
    def search(self, 
                query={}, 
                returnFields=None, 
                returnFormat=None,
                nbResults=-1,
                collection=None):
        """
        Search for data in HAL archives based on the specified parameters.

        Args:
            query (dict): The search text as dictionnary of key/value pairs from allowed queries.
            returnFields (str, optional): The fields to include in the search results. Defaults to None.
            returnFormat (str, optional): The return format of the search results. Defaults defined for each type of DB.
            nbResults (int/list, optional): The number of results to return or list of start/end. Defaults to -1.
            collection (str, optional): The collection to search in. Defaults to None.
        Returns:
            list or dict or str: The search results based on the specified return format.

        """
        self.setQuery(query)
        self.setReturnFormat(returnFormat)
        self.setReturnFields(returnFields)
        self.setNbResults(nbResults)
        self.setCollection(collection)
        # run url's request
        response = self.getAllResults()
        return response
        
    def basicSearch(self, 
                    txtsearch=None, 
                    returnFields=None, 
                    returnFormat=None, 
                    collection=None):
        """ Basic search in HAL API """
        if txtsearch is None:
            logger.warning("No search text provided")
            txtsearch = ""  
        # run search with predefined query
        basicQuery = {self.defaultQueryType: txtsearch}
        data = self.search(query=basicQuery, 
                           returnFields=returnFields, 
                           returnFormat=returnFormat, 
                           collection=collection)
        return data
    
class APIHAL(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOC
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_DOC
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_DOC
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_DOC
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_DOC
    
    def __repr__(self) -> str:
        return "HAL API class for documents"   
     
    def __str__(self) -> str:
        return "HAL API class for documents"
    
        
    def getBaseUrl(self):        
        """ Update base url with collection if provided"""
        baseurl = self.url
        if self.collection:
            baseurl.args['collection'] = self.collection.set(path=self.collection)
        return baseurl.url
    
class APIHALauthor(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_AUTHOR
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_AUTHOR
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_AUTHOR
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_AUTHOR
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_AUTHOR
    
    def __repr__(self) -> str:
        return "HAL API class for authors"   
     
    def __str__(self) -> str:
        return "HAL API class for authors"
class APIHALauthorstructure(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_AUTHORSTRUCTURE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_AUTHORSTRUCTURE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_AUTHORSTRUCTURE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_AUTHORSTRUCTURE
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_AUTHORSTRUCTURE
    
    def __repr__(self) -> str:
        return "HAL API class for structures of authors"   
     
    def __str__(self) -> str:
        return "HAL API class for structures of authors"
class APIHALanr(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['anr'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_ANR
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_ANR
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_ANR
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_ANR
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_ANR
    
    def __repr__(self) -> str:
        return "HAL API class for ANR projects"   
     
    def __str__(self) -> str:
        return "HAL API class for ANR projects"
class APIHALeuropeanproject(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['europeanproject'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_EUROPEANPROJECT
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_EUROPEANPROJECT
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_EUROPEANPROJECT
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_EUROPEANPROJECT
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_EUROPEANPROJECT

    def __repr__(self) -> str:
        return "HAL API class for european projects"   
     
    def __str__(self) -> str:
        return "HAL API class for european projects"
class APIHALdoctype(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['doctype'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOCTYPE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_DOCTYPE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_DOCTYPE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_DOCTYPE
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_DOCTYPE

    def __repr__(self) -> str:
        return "HAL API class for document types"   
     
    def __str__(self) -> str:
        return "HAL API class for document types"
    
    def getAllResults(self,params=None):
        """ Get all results for a query """
        if not params:
            params = self.getParams()
        return self.getUrlRequest(params)

class APIHALdomain(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['domain'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_DOMAIN
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_DOMAIN
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_DOMAIN
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_DOMAIN
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_DOMAIN
    
    def __repr__(self) -> str:
        return "HAL API class for domains"   
     
    def __str__(self) -> str:
        return "HAL API class for domains"

class APIHALinstance(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['instance'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_INSTANCE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_INSTANCE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_INSTANCE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_INSTANCE
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_INSTANCE

    def __repr__(self) -> str:
        return "HAL API class for instances"   
     
    def __str__(self) -> str:
        return "HAL API class for instances"
class APIHALjournal(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['journal'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_JOURNAL
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_JOURNAL
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_JOURNAL
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_JOURNAL
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_JOURNAL

    def __repr__(self) -> str:
        return "HAL API class for journals"   
     
    def __str__(self) -> str:
        return "HAL API class for journals"
class APIHALmetadata(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['metadata'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_METADATA
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_METADATA
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_METADATA
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_METADATA
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_METADATA

    def __repr__(self) -> str:
        return "HAL API class for metadata"   
     
    def __str__(self) -> str:
        return "HAL API class for metadata"
    
    def getAllResults(self,params=None):
        """ Get all results for a query """
        if not params:
            params = self.getParams()
        return self.getUrlRequest(params)
    
class APIHALmetadatalist(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['metadatalist'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_METADATALIST
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_METADATALIST
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_METADATALIST
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_METADATALIST
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_METADATALIST

    def __repr__(self) -> str:
        return "HAL API class for metadata list"   
     
    def __str__(self) -> str:
        return "HAL API class for metadata list"
class APIHALstructure(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['structure'])
        self.ALLOWED_RETURN_FORMATS = dflt.HAL_API_ALLOWED_RETURN_FORMATS_STRUCTURE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_STRUCTURE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_STRUCTURE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_STRUCTURE
        self.defaultReturnFormat = dflt.HAL_API_DEFAULT_RETURN_FORMAT_STRUCTURE
    
    def __repr__(self) -> str:
        return "HAL API class for structures"   
     
    def __str__(self) -> str:
        return "HAL API class for structures"
  
        
    
def loadAPI(usecase="article"):
    logger.debug("Searching in database: {}".format(usecase))
    if usecase == "journal":
        apiObj = APIHALjournal()
    elif usecase == "article":        
        apiObj = APIHAL()
    elif usecase == "anrproject":
        apiObj = APIHALanr()
    elif usecase == "authorstruct":
        apiObj = APIHALauthorstructure()
    elif usecase == "europeanproject":
        apiObj = APIHALauthor()
    elif usecase == "doctype":
        apiObj = APIHALdoctype()
    elif usecase == "domain":
        apiObj = APIHALdomain()
    elif usecase == "instance":
        apiObj = APIHALinstance()
    elif usecase == "metadata":
        apiObj = APIHALmetadata()
    elif usecase == "metadatalist":
        apiObj = APIHALmetadatalist()
    elif usecase == "structure":
        apiObj = APIHALstructure()
    else:
        logger.warning("Unknown database: {}".format(usecase))
        logger.warning("Authorized database: {}".format(["journal",
                                                         "article",
                                                         "anrproject",
                                                         "authorstruct",
                                                         "europeanproject",
                                                         "doctype",
                                                         "domain",
                                                         "instance",
                                                         "metadata",
                                                         "metadatalist",
                                                         "structure"]))        
        apiObj = None
    return apiObj
            
def checkDoiInHAL(doi=None):
    """ Check if doi is in HAL 
    Args:
    doi (str): The DOI to check.

    Returns:
    bool: True if the DOI is already in HAL, False otherwise.
    """
    if not doilib.validate_doi(doi):
        logger.warning("Invalid DOI: {}".format(doi))
    #
    # append hal ID as return
    apiObj = APIHAL()
    data = apiObj.search(query={"doi": doi},
                    returnFields="halId_s",
                    returnFormat="json"
                    )
    returndata = None
    if data:
        returndata = data[0].get("halId_s", None)
    return returndata


def choose_from_results(
    results, forceSelection=False, maxNumber=dflt.DEFAULT_MAX_NUMBER_RESULTS
):
    """
    Interactive selection of a result from a list of results.

    Args:
        results (list): A list of results to choose from.
        forceSelection (bool, optional): If True, a result will be automatically selected. Defaults to False.
        maxNumber (int, optional): The maximum number of results to display. Defaults to the default maximum number.

    Returns:
        selected_result: The selected result from the list, or a manually provided title.

    """
    logger.info(dflt.TXT_SEP)
    logger.info("Multiple results found:")
    # lambda show info
    funShow = lambda x, y: "[{}/{}]. {} - {}".format(
        x + 1, len(results), y.get("label_s", "N/A"), result.get("halId_s", "N/A")
    )
    #
    lastposition = 0
    for i, result in enumerate(results):
        # print only the first maxNumber results
        if i < maxNumber:
            logger.info(funShow(i, result))
            lastposition = i
        else:
            break

    logger.info(
        "Select a number to view details (0 to skip or p/n for previous/next selection or m for manual definition): "
    )

    choiceOK = False
    while not choiceOK:
        # if selection is forced: first result used
        if forceSelection:
            choice = "1"
            choiceOK = True
        else:
            choice = input(" > ")
        # depending on the input
        if choice.isdigit() and 0 <= int(choice) <= len(results):
            selected_result = results[int(choice) - 1]
            return selected_result
        elif choice == "m":
            logger.info("Provide title manually")
            manualTitle = input(" > ")
            return manualTitle
        elif choice == "p":
            logger.info("Previous selection")
            if lastposition - 1 >= 0:
                lastposition -= 1
            else:
                logger.warning("No previous selection.")
            logger.info(funShow(lastposition, results[lastposition]))
        elif choice == "n":
            logger.info("Next selection")
            if lastposition + 1 < len(results):
                lastposition += 1
            else:
                logger.warning("No next selection.")
            logger.info(funShow(lastposition, results[lastposition]))
        else:
            logger.warning("Invalid choice.")

    return None


class AnalyseResponse():
    """ Manage response from HAL API """
    def __init__(self, response):
        self.response = response
        self.ok = False
        self.message = ""
        self.checkResponse()

    def checkResponse(self):
        e = self.response.status_code
        if self.response.status_code == 200:
            self.ok = True
            # detect formatting
            if "application/json" in self.response.headers.get("Content-Type"):
                if self.response.json().get('Error',False):
                    self.ok = False
                    self.message = self.response.json().get('Error')
        elif self.response.status_code == 201:
            self.ok = True
            # logger.info("Successfully upload to HAL.")
            pass
        elif self.response.status_code == 202:
            self.ok = True
            # logger.info("Note accepted by HAL.")
            pass
        elif self.response.status_code == 401:
            # logger.info("Authentification refused - check credentials")
            e = os.EX_SOFTWARE
        elif self.response.status_code == 400:
            # logger.info("Internal error - check XML file")
            e = os.EX_SOFTWARE
        else:
            self.ok = False
            self.message = self.response.text \
                +'\n' \
                +'[{}] - {}'.format(self.response.status_code, self.response.reason)
        return e


