![Firefly push2HAL-ordinateur 55689](https://github.com/luclaurent/push2HAL/assets/147177/40f90c82-8d19-47ba-aa70-982765632942)

`push2HAL` is a basic Python library dedicated to achieving upload on [HAL](https://hal.science) database. It will use the classical API of HAL to get information and the SWORD one to upload content. Two main executables are provided (for UNIX use only):

- `pdf2hal` is able to upload a PDF file to an existing notice on HAL. 
- `json2hal` is able to build the necessary data from a JSON file to create a new notice in HAL and upload it directly with or without providing a PDF file.

## `pdf2hal` - Upload PDF file to an existing notice in HAL 

`pdf2hal` proposes an interactive mode to upload a PDF to the right/selected notice in HAL by extracting basic data from the PDF file and executing search on HAL database

## Usage:

```
usage: pdf2hal [-h] [-a HALID] [-c CREDENTIALS] [-v] [-e] [-l LOGIN] [-p PASSWD] [-f] pdf_path
```

#### Arguments

- positional argument:
  `pdf_path`               Path to the PDF file

- optional arguments:

|short|long|default|help|
| :--- | :--- | :--- | :--- |
|`-h`|`--help`||show this help message and exit|
|`-a`|`--halid`|`None`|HALid of document to update|
|`-c`|`--credentials`|`None`|Path to the credentials file|
|`-v`|`--verbose`||Show all logs|
|`-e`|`--prod`||Execute on production server (use with caution)|
|`-t`|`--test`||Execute on prod server as test (dryrun)|
|`-l`|`--login`|`None`|Username for API (HAL)|
|`-p`|`--passwd`|`None`|Password for API (HAL)|
|`-cc`|`--complete`|`None`|Run completion (use grobid, idext or affiliation or list of terms separated by comma)|
|`-id`|`--idhal`|`None`|idHal to link deposit to specific user


## `json2hal` - Create a new note on HAL w/- or w/o additional file

`json2hal` is able to create a note on HAL based on content provided in a JSON file. Additional (PDF) could be provided and uploaded on the same time

## Usage:

```
usage: json2hal [-h] [-c CREDENTIALS] [-v] [-e] [-t] [-l LOGIN] [-p PASSWD] [-cc COMPLETE] [-id IDHAL] json_path
```

#### Arguments

- positional argument:
  `json_path`               Path to the JSON file

- optional arguments:

|short|long|default|help|
| :--- | :--- | :--- | :--- |
|`-h`|`--help`||show this help message and exit|
|`-c`|`--credentials`|`None`|Path to the credentials file|
|`-v`|`--verbose`||Show all logs|
|`-e`|`--prod`||Execute on production server (use with caution)|
|`-t`|`--test`||Execute on prod server as test (dryrun)|
|`-l`|`--login`|`None`|Username for API (HAL)|
|`-p`|`--passwd`|`None`|Password for API (HAL)|
|`-cc`|`--complete`|`None`|Run completion (use grobid, idext or affiliation or list of terms separated by comma)|
|`-id`|`--idhal`|`None`|idHal to link deposit to specific user|



## **Note that:**
    
- HAL credentials (for production or pre-production server) could be provided using `.apihal` based on JSON syntax (see `.apihal_example`)
- by default, the [preprod server][1] is used (argument `-e` use the [production server][2])
- a test mode on production server could be used by give argument `-t`

[1]: [https://api-preprod.archives-ouvertes.fr/](https://api-preprod.archives-ouvertes.fr/)
[2]: [https://api.archives-ouvertes.fr/](https://api.archives-ouvertes.fr/)
  
## Installation

`push2HAL` could be installed by downloading this repository and run `pip install .` in the root folder of it.

## Requirements:

`push2HAL` requires external modules. They can be installed using `pip install -r requirements` or could be installed directly using `pip install`

## References

The tools have been developed by considering documentation:
- [SWORD implementation in HAL](https://api.archives-ouvertes.fr/docs/sword)
- [XSD validation format for HAL](https://hal.archives-ouvertes.fr/documents/aofr.xsd)
- [XML integration documentation for HAL](https://api.archives-ouvertes.fr/documents/all.xml)
- [common XML files for HAL](https://github.com/CCSDForge/HAL/tree/master/Sword)
- [HAL referential](https://api.archives-ouvertes.fr/docs/ref)
- [HAL API syntax for searching](https://api.archives-ouvertes.fr/docs/search)
