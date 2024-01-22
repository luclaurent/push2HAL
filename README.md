# uploadHAL

PDF2HAL - Upload PDF file to HAL 
# Usage:


```bash
usage: ./pdf2hal [-h] [-c CREDENTIALS] [-v] [-e] [-l LOGIN] [-p PASSWD] [-f] pdf_path

```
# Arguments

|short|long|default|help|
| :--- | :--- | :--- | :--- |
|`-h`|`--help`||show this help message and exit|
|`-c`|`--credentials`|`None`|Path to the credentials file|
|`-v`|`--verbose`||Show all logs|
|`-e`|`--prod`||Execute on prod server|
|`-l`|`--login`|`None`|Username for API (HAL)|
|`-p`|`--passwd`|`None`|Password for API (HAL)|
|`-f`|`--force`||Force for no interaction (use first result from HAL)|

Note that:
    
- credentials could be provided using `.apihal` based on json syntax (see `.apihal_example)
- by default the preprod server is used

## Requirements:

PDF2HAL requires external modules. They can be installed using `pip install -r requirements`