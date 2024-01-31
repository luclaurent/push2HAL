# uploadHAL

`uploadHAL` is a basic Python library dedicated to achieve upload on [HAL](https://hal.science) database. It will use the classical API of HAL to get information and the SWORD one to upload content. Two main executables are provided (for UNIX use only):

- `pdf2hal` is able to upload a PDF file to an existing notice on HAL. 
- `json2hal` is able to build necessary data to create a new notice in HAL and upload it directly with or without providing a PDF file.

## `pdf2hal` - Upload PDF file to an existing notice in HAL

## Usage:

```
usage: pdf2hal [-h] [-a HALID] [-c CREDENTIALS] [-v] [-e] [-l LOGIN] [-p PASSWD] [-f] pdf_path
```

#### Arguments

|short|long|default|help|
| :--- | :--- | :--- | :--- |
|`-h`|`--help`||show this help message and exit|
|`-a`|`--halid`|`None`|HALid of document to update|
|`-c`|`--credentials`|`None`|Path to the credentials file|
|`-v`|`--verbose`||Show all logs|
|`-e`|`--prod`||Execute on prod server|
|`-l`|`--login`|`None`|Username for API (HAL)|
|`-p`|`--passwd`|`None`|Password for API (HAL)|
|`-f`|`--force`||Force for no interaction (Use with caution, it can lead to upload to the wrong place)|

**Note that:**
    
- HAL  credentials (for production or pre-predoction server) could be provided using `.apihal` based on json syntax (see `.apihal_example`)
- by default the [preprod server][1] is used (argument `-e` use the [production server][2])

[1] [https://api-preprod.archives-ouvertes.fr/](https://api-preprod.archives-ouvertes.fr/)
[1] [https://api.archives-ouvertes.fr/](https://api.archives-ouvertes.fr/)
  
## Installation

`uploadHAL` could be installed by downloading this repository and run `pip install .` in the root folder of it.

## Requirements:

`uploadHAL` requires external modules. They can be installed using `pip install -r requirements` or could be installed directly using `pip install`