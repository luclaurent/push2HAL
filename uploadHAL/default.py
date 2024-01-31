####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of uploadHAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/uploadHAL
####*****************************************************************************************
####*****************************************************************************************


DEFAULT_NB_CHAR = 400
TXT_SEP = "++++++++++++++++++++++"

DEFAULT_CREDENTIALS_FILE = ".apihal"
DEFAULT_UPLOAD_FILE_NAME_PDF = "{}.pdf"  #'upload.pdf'
DEFAULT_UPLOAD_FILE_NAME_XML = "upload.xml"
DEFAULT_UPLOAD_FILE_NAME_ZIP = "upload"
DEFAULT_MAX_NUMBER_RESULTS = (
    5  # results to display when searching in archives-ouvertes.fr
)
DEFAULT_MAX_NUMBER_RESULTS_QUERY = (
    50  # results to query when searching in archives-ouvertes.fr
)

DEFAULT_XML_SWORD_PACKAGING = "http://purl.org/net/sword-types/AOfr"
DEFAULT_CONTENT_DISPOSITION='none'
DEFAULT_EXPORT_ARCHIVE='false'
DEFAULT_EXPORT_PMC='false'
DEFAULT_HIDE_REPEC='false'
DEFAULT_HIDE_OAI='false'
DEFAULT_ALLOW_COMPLETION='false'

DEFAULT_VALIDATION_XSD = 'aofr.xsd'
DEFAULT_NAMESPACE_XML = {None: 'http://www.tei-c.org/ns/1.0'}#, 'tei': 'http://www.tei-c.org/ns/1.0' , 'hal':'http://hal.archives-ouvertes.fr'} #{"tei": "http://www.tei-c.org/ns/1.0"}
DEFAULT_XML_LANG = "{http://www.w3.org/XML/1998/namespace}"
DEFAULT_ERROR_DESCRIPTION_SWORD_LOC = "sword:verboseDescription"
HAL_API_BASE = "https://api.archives-ouvertes.fr/"
HAL_API_SEARCH_URL = HAL_API_BASE+"search/"
HAL_API_ANR_URL = HAL_API_BASE+"ref/anrproject/"
HAL_API_AUTHOR_URL = HAL_API_BASE+"ref/author/"
HAL_API_AUTHORSTRUCT_URL = HAL_API_SEARCH_URL+"authorstructure/"
HAL_API_EUROPPROJ_URL = HAL_API_BASE+"ref/europeanproject/"
HAL_API_DOC_URL = HAL_API_BASE+"ref/doctype/"
HAL_API_DOMAIN_URL = HAL_API_BASE+"ref/domain/"
HAL_API_INSTANCE_URL = HAL_API_BASE+"ref/instance/"
HAL_API_JOURNAL_URL = HAL_API_BASE+"ref/journal/"
HAL_API_METADATA_URL = HAL_API_BASE+"ref/metadata/"
HAL_API_METADATALIST_URL = HAL_API_BASE+"ref/metadatalist/"
HAL_API_STRUCTURE_URL = HAL_API_BASE+"ref/structure/"
HAL_TEI_URL = "https://api.archives-ouvertes.fr/oai/TEI/{hal_id}"
HAL_SWORD_API_URL = "https://api.archives-ouvertes.fr/sword/hal/"
HAL_SWORD_PRE_API_URL = "https://api-preprod.archives-ouvertes.fr/sword/hal/"

ID_ORCID_URL='http://orcid.org/'
ID_ARXIV_URL='http://arxiv.org/a/'
ID_RESEARCHERID_URL='http://www.researcherid.com/rid/'
ID_IDREF_URL='http://www.idref.fr/'
ID_CC_URL='https://creativecommons.org/licenses/'

DEFAULT_AUDIENCE='1'
DEFAULT_INVITED='0'
DEFAULT_POPULAR='0'
DEFAULT_PEER='0'
DEFAULT_PROCEEDINGS='0'
DEFAULT_STRUCT_TYPE='institution'
