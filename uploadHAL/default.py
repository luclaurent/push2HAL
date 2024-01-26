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
DEFAULT_NAMESPACE_XML = {"tei": "http://www.tei-c.org/ns/1.0"}
DEFAULT_ERROR_DESCRIPTION_SWORD_LOC = "sword:verboseDescription"
ARCHIVES_API_URL = "https://api.archives-ouvertes.fr/search/"
ARCHIVES_TEI_URL = "https://api.archives-ouvertes.fr/oai/TEI/{hal_id}"
ARCHIVES_SWORD_API_URL = "https://api.archives-ouvertes.fr/sword/hal/"
ARCHIVES_SWORD_PRE_API_URL = "https://api-preprod.archives-ouvertes.fr/sword/hal/"
