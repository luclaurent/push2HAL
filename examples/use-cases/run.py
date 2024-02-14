import requests
from urllib.parse import urljoin, urlencode, urlparse, urlunparse
import pickle
from push2HAL import libHAL, execHAL,misc
import os
import pathlib
import json

import libConvert

saveDir = "data"
pathlib.Path(saveDir).mkdir(parents=True, exist_ok=True)

if True:
    # get full list of papers in journal
    with open('.api_springer','r') as f: 
        api_key = f.read()
    journal_id = "40323"
    url_base = "http://api.springernature.com/"
    api_arg = "meta/v2/json"
    api_arg_journal = "?q=journalid:"
    api_arg_doi = "?q=doi:"
    api_arg_key = "&api_key="
    # full url journal's request
    full_url_journal = urljoin(
        url_base, api_arg + api_arg_journal + journal_id + api_arg_key + api_key
    )
    headers = {"Accept": "application/json"}
    r = requests.get(full_url_journal, headers=headers)
    # print("Response: {}",format(r.json()))
    # full url journal's request
    article_list = r.json()["records"]
    # iterate over pages
    for page in range(1, int(r.json()["result"][0]["total"])):
        # full url journal's request
        next_page_arg = r.json().get("nextPage")
        if next_page_arg:
            full_url_journal = urljoin(url_base, next_page_arg)
            r = requests.get(full_url_journal, headers=headers)
            jsonData = r.json()
            print("Response: {}".format(jsonData))
            article_list.extend(r.json()["records"])
        else:
            break

        # store results
        file = open(os.path.join(saveDir, "article_list.pck"), "wb")
        pickle.dump(article_list, file)
        file.close()

        # show articles
        # list articles
        for art in article_list:
            print(
                "Article: {} - Collection: {}".format(
                    art["title"], art["topicalCollection"]
                )
            )

if True:
    # load pickle
    article_list = pickle.load(
        open(os.path.join(saveDir, "article_list.pck"), "rb")
    )
    # extract article within collection
    article_list_collection = [
        art for art in article_list if art["topicalCollection"] != ""
    ]
    article_list_not_collection = [
        art for art in article_list if art["topicalCollection"] == ""
    ]
    # save
    file = open(os.path.join(saveDir, "article_list_collection.pck"), "wb")
    pickle.dump(article_list_collection, file)
    file.close()
    file = open(os.path.join(saveDir, "article_list_not_collection.pck"), "wb")
    pickle.dump(article_list_collection, file)
    file.close()

if True:
    # load pickle
    article_list_collection = pickle.load(
        open(os.path.join(saveDir, "article_list_collection.pck"), "rb")
    )
    # check if article is in HAL
    article_list_in_hal = list()
    article_list_notin_hal = list()
    for art in article_list_collection:
        if libHAL.checkDoiInHAL(art["doi"]):
            article_list_in_hal.append(art)
        else:
            article_list_notin_hal.append(art)
    #
    file = open(os.path.join(saveDir, "article_list_in_hal.pck"), "wb")
    pickle.dump(article_list_in_hal, file)
    file.close()
    file = open(os.path.join(saveDir, "article_list_notin_hal.pck"), "wb")
    pickle.dump(article_list_notin_hal, file)
    file.close()
    #
    print("Articles in HAL: {}".format(len(article_list_in_hal)))
    print("Articles not in HAL: {}".format(len(article_list_notin_hal)))

if True:
    # load pickle
    article_list = pickle.load(
        open(os.path.join(saveDir, "article_list_notin_hal.pck"), "rb")
    )
    # along articles
    for art in article_list:
        try:
            # convert to HAL
            json_file = libConvert.buildJSON(art,'json',os.path.join('json','pdf'))

            # push to HAL from json
            idHal = execHAL.runJSON2HAL(
                json_file,
                verbose=True,
                prod="prod",
                credentials=misc.load_credentials(),#
                completion="idext,affiliation", # or false
                idhal=None,
            )
            # push idhal to json
            data = json.loads(open(json_file).read())
            data['doc_idhal'] = idHal
            json_object = json.dumps(data, indent=4)
            with open(json_file, "w") as outfile:
                outfile.write(json_object)
        except:
            print("Error with article: {}".format(art["doi"]))
          
