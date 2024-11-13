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
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE
        self.defaultReturnFields = [] ## default value(s) provided by HAL API
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE
        self.collection = None
        self.query = None
        self.returnFields = None
        self.returnType = None
        self.lastResponse = None
        self.lastParams = None
        self.nbElements = dflt.DEFAULT_MAX_NUMBER_RESULTS_QUERY
        
    def showConfig(self):
        """ Show the configuration of the current HAL API """
        logger.info("{}".format("="*len(str(self))))
        logger.info("{}".format(self))
        logger.info("{}".format("="*len(str(self))))
        logger.info('Current configuration')
        logger.info(' + URL: {}'.format(self.getBaseUrl()))
        logger.info(' + Defined query: {}'.format(m.showItem(self.query)))
        logger.info(' + Defined return fields: {}'.format(m.showItem(self.returnFields)))
        logger.info(' + Defined return type: {}'.format(self.returnType))
        logger.info("{}".format("="*len(str(self))))
        logger.info('Last request')
        logger.info(' + Last Response: {}'.format(self.lastResponse)) 
        logger.info(' + Last Params: {}'.format(m.showItem(self.lastParams)))
        logger.info("{}".format("="*len(str(self))))
        logger.info('Allowed items')
        logger.info(' + Allowed return types: {}'.format(self.ALLOWED_RETURN_TYPES))
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
        if nbResults >= 0:
            self.nbElements = nbResults
        else:
            self.nbElements = dflt.DEFAULT_MAX_NUMBER_RESULTS_QUERY
    
    def setReturnFormat(self, typeR="json"):
        """ Set the return type of the HAL API """
        if typeR in self.ALLOWED_RETURN_TYPES:
            logger.debug('Return typeset : {}'.format(typeR))
            self.returnType = typeR                
        else:            
            logger.warning("Unknown return type: {} for {}".format(typeR,self))
            logger.warning("Force to use {}".format(self.defaultReturnType))
            self.returnType = self.defaultReturnType
            
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
            self.returnFields.extend(returnFields)
        else:
            self.returnFields = returnFields
            
    
    def setQuery(self, querytype="title_approx"):
        """ Set the appropriate syntax for query of HAL API """
        if querytype in list(self.ALLOWED_QUERY_TYPES.keys()):
            self.query = dflt.HAL_API_ALLOWED_QUERY_TYPES[querytype]
            self.querytype = querytype
        else:
            logger.warning("Unknown searching type {}".format(querytype))
            self.query = dflt.HAL_API_ALLOWED_QUERY_TYPES["title_approx"]
            self.querytype = "title_approx"
            
    def formatData(self, response):
        """ Format response depending on return type """
        if response.status_code == 200:
            if self.getReturnType() == "json":
                data = response.json().get("response", {}).get("docs", [])
            elif self.getReturnType() == "xml-tei" or self.getReturnType() == "xml":
                dataTmp = response.text
                # declare namespace
                # key, value = list(dflt.DEFAULT_NAMESPACE_XML.items())[0]
                # etree.register_namespace(key, value)
                data = etree.fromstring(dataTmp.encode("utf-8"))
        else:
            data = []
        return data
    
    def getReturnFields(self):
        return ','.join(self.returnFields)
    
    def getReturnType(self):
        if self.returnType is None:
            logger.warning('No return type set, return {}'.format(self.defaultReturnType))
            return self.defaultReturnType
        else:
            return self.returnType
        
    def getBaseQuery(self):
        baseQuery = ''
        if type(self.query) is dict:
            for key, value in self.query.items():
                baseQuery += ",{}:{}".format(key, value)
        return baseQuery    
        
    def getParams(self):
        """ Get the parameters for the URL request for the HAL API request """
        # get query
        query = self.getBaseQuery()
        # get return type
        typeR = self.getReturnType()
        # get return fields
        returnFields = self.getReturnFields()
        # build full query
        params = {
            "q": query,
            "fl": returnFields,
            "wt": typeR,
            "rows": self.nbElements,  # Adjust the number of rows based on your preference
        }        
        return params
    
    def getBaseUrl(self):
        return self.url
        
    def getUrlRequest(self, params=None):
        """ Make the request to the HAL API """
        if not params:
            params = self.getParams()
        response = requests.get(self.getBaseUrl(), params=params)
        #
        self.lastResponse = response
        self.lastParams = params
        #
        if response.status_code != 200:
            logger.warning('Error on url request: {}'.format(response.status_code))
        return self.formatData(response)
    
    def search(self, 
                query={}, 
                returnFields=None, 
                returnType=None,
                nbResults=-1,
                collection=None):
        """
        Search for data in HAL archives based on the specified parameters.

        Args:
            query (dict): The search text as dictionnary of key/value pairs from allowed queries.
            returnFields (str, optional): The fields to include in the search results. Defaults to None.
            returnType (str, optional): The return format of the search results. Defaults defined for each type of DB.
            collection (str, optional): The collection to search in. Defaults to None.
        Returns:
            list or dict or str: The search results based on the specified return format.

        """
        self.setQuery(query)
        self.setReturnType(returnType)
        self.setReturnFields(returnFields)
        self.setNbResults(nbResults)
        self.setCollection(collection)
        # run url's request
        response = self.getUrlRequest()
        return response
        
    def basicSearch(self, 
                    txtsearch=None, 
                    returnFields=None, 
                    returnType=None, 
                    collection=None):
        """ Basic search in HAL API """
        if txtsearch is None:
            logger.warning("No search text provided")
            txtsearch = ""  
        # run search with predefined query
        basicQuery = {self.defaultQueryType: txtsearch}
        data = self.search(query=basicQuery, 
                           returnFields=returnFields, 
                           returnType=returnType, 
                           collection=collection)
        return data
    
class APIHAL(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_DOC
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_DOC
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_DOC
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_DOC
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_DOC
        
    def getBaseUrl(self):        
        """ Update base url with collection if provided"""
        baseurl = super().getBaseUrl()
        if self.collection:
            baseurl.args['collection'] = self.collection.set(path=self.collection)
        return baseurl
    
class APIHALauthor(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_AUTHOR
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_AUTHOR
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_AUTHOR
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_AUTHOR
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_AUTHOR
    
class APIHALauthorstructure(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_AUTHORSTRUCTURE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_AUTHORSTRUCTURE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_AUTHORSTRUCTURE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_AUTHORSTRUCTURE
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_AUTHORSTRUCTURE

class APIHALanr(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_ANR
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_ANR
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_ANR
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_ANR
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_ANR
    
class APIHALeuropeanproject(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_EUROPEANPROJECT
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_EUROPEANPROJECT
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_EUROPEANPROJECT
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_EUROPEANPROJECT
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_EUROPEANPROJECT
    
class APIHALdoctype(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_DOCTYPE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_DOCTYPE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_DOCTYPE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_DOCTYPE
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_DOCTYPE
    
class APIHALdomain(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_DOMAIN
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_DOMAIN
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_DOMAIN
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_DOMAIN
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_DOMAIN
    
class APIHALinstance(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_INSTANCE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_INSTANCE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_INSTANCE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_INSTANCE
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_INSTANCE
    
class APIHALjournal(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_JOURNAL
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_JOURNAL
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_JOURNAL
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_JOURNAL
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_JOURNAL
    
class APIHALmetadata(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_METADATA
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_METADATA
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_METADATA
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_METADATA
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_METADATA
    
class APIHALmetadatalist(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_METADATALIST
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_METADATALIST
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_METADATALIST
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_METADATALIST
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_METADATALIST
    
class APIHALstructure(APIHALbase):
    def __init__(self):
        super().__init__()
        self.url = furl(dflt.HAL_API_URL['search'])
        self.ALLOWED_RETURN_TYPES = dflt.HAL_API_ALLOWED_RETURN_TYPES_STRUCTURE
        self.ALLOWED_QUERY_TYPES = dflt.HAL_API_ALLOWED_QUERY_TYPES_STRUCTURE
        self.ALLOWED_RETURN_FIELDS = dflt.HAL_API_ALLOWED_RETURN_FIELDS_STRUCTURE
        self.defaultQueryType = dflt.HAL_API_DEFAULT_QUERY_TYPE_STRUCTURE
        self.defaultReturnType = dflt.HAL_API_DEFAULT_RETURN_TYPE_STRUCTURE
    

  
        
    
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
            

            
            

        

    

    

    

            
        

        

           
    
def checkDoiInHAL(self, doi=None):
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
    data = apiObj.search(query={"doi_s": doi},
                  returnFields="halId_s",
                  returnType="json"
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


def manageError(e):
    """ Manage return code from upload2HAL """
    if e == 201:
        # logger.info("Successfully upload to HAL.")
        pass
    elif e == 202:
        # logger.info("Note accepted by HAL.")
        pass
    elif e == 401:
        # logger.info("Authentification refused - check credentials")
        e = os.EX_SOFTWARE
    elif e == 400:
        # logger.info("Internal error - check XML file")
        e = os.EX_SOFTWARE
    return e


