from lxml import etree
import re
import logging

FORMAT = '%(asctime)s  %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
Logger = logging.getLogger('json2hal')


ID_ORCID_URL='http://orcid.org/''
ID_ARXIV_URL='http://arxiv.org/a/'
ID_RESEARCHERID_URL='http://www.researcherid.com/rid/'
ID_IDREF_URL='http://www.idref.fr/'
ID_CC_URL='https://creativecommons.org/licenses/'

DEFAULT_AUDIENCE='1'
DEFAULT_INVITED='0'
DEFAULT_POPULAR='0'
DEFAULT_PEER='0'
DEFAULT_PROCEEDINGS='0'

def setTitles(nInTree,titles):
    nTitle = list()
    if titles == dict:
        for l,t in titles.items():
            nTitle.append(etree.SubElement(nInTree, "title"))
            nTitle[-1].set("xml:lang",l)
            nTitle[-1].text = t
    else:
        Logger.warning("No language for title: force english")
        nTitle.append(etree.SubElement(nInTree, "title"))
        nTitle[-1].set("xml:lang","en")
        nTitle[-1].text = titles
    return nTitle
    
def setSubTitles(nInTree,titles):
    nTitle = list()
    if titles == dict:
        for l,t in titles.items():
            nTitle.append(etree.SubElement(nInTree, "title"))
            nTitle[-1].set("type","sub")
            nTitle[-1].set("xml:lang",l)
            nTitle[-1].text = t
    else:
        Logger.warning("No language for title: force english")
        nTitle.append(etree.SubElement(nInTree, "title"))
        nTitle[-1].set("type","sub")
        nTitle[-1].set("xml:lang","en")
        nTitle[-1].text = titles
    return nTitle

def setAuthors(inTree,authors):
    nAuthors = list()
    for a in authors:
        nAuthors.append(etree.SubElement(inTree, "author"))
        # roles: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:relator&fl=*&wt=xml
        if "role" in a:
            nAuthors[-1].set("role",a["role"])
        else:
            Logger.warning("No role for author {} {}: force aut".format(a["name"][0],a["name"][-1]))
            nAuthors[-1].set("role","aut")
        persName = etree.SubElement(nAuthors[-1], "persName")
        forename = etree.SubElement(persName, "forename")
        forename.set("type","first")
        forename.text = a["name"][0]
        if len(a["name"])>2:
            forename = etree.SubElement(persName, "forename")
            forename.set("type","middle")
            forename.text = a["name"][1]
        surename = etree.SubElement(persName, "surename")
        surename.text = a[-1]
        if "email" in a:
            idA = etree.SubElement(nAuthors[-1], "email")
            idA.text = a["email"]
        if "idhal" in a:
            idA = etree.SubElement(nAuthors[-1], "idno")
            idA.set("type","idhal")
            idA.text = a["idhal"]
        if "halauthor" in a:
            idA = etree.SubElement(nAuthors[-1], "idno")
            idA.set("type","halauthor")
            idA.text = a["halauthor"]
        if "url" in a:
            idA = etree.SubElement(nAuthors[-1], "ptr")
            idA.set("type","url")
            idA.set("target",a["url"])
        if "orcid" in a:
            idA = etree.SubElement(nAuthors[-1], "idno")
            idA.set("type",ID_ORCID_URL)
            idA.text = a["orcid"]
        if "arxiv" in a:
            idA = etree.SubElement(nAuthors[-1], "idno")
            idA.set("type",ID_ARXIV_URL)
            idA.text = a["arxiv"]
        if "researcherid" in a:
            idA = etree.SubElement(nAuthors[-1], "idno")
            idA.set("type",ID_RESEARCHERID_URL)
            idA.text = a["researcherid"]
        if "idref" in a:
            idA = etree.SubElement(nAuthors[-1], "idno")
            idA.set("type",ID_IDREF_URL)
            idA.text = a["idref"]
        if "affiliation" in a:
            if type(a["affiliation"]) is not list:
                list_aff = [a["affiliation"]]
            else:
                list_aff = a["affiliation"]
            for aff in list_aff:
                nAff = etree.SubElement(nAuthors[-1], "affiliation")
                if 'structHal' in aff:
                    idStrut = aff['structHal']
                    idStruct = re.sub('^#struct-','',idStrut)
                    nAff.set("ref",'#struct-'+idStruct)
                elif 'locAff' in aff:
                    nAff.set("ref",'#localStruct-'+aff['locAff'])
    return nAuthors
                
def setLicense(inTree,license):
    availability = etree.SubElement(inTree, "availability")
    lic_cc = etree.SubElement(availability, "license")
    # all licenses: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:licence&fl=*&wt=xml
    lic_cc.set('target',ID_CC_URL+'/'+license["version"]+'/')
    
def setStamps(inTree,stamps):
    nStamps = list()
    if type(stamps) is not list:
        list_stamps = [stamps]
    else:
        list_stamps = stamps
    for s in list_stamps:
        nStamps.append(etree.SubElement(inTree, "idno"))
        nStamps[-1].set("type","stamp")
        nStamps[-1].set("n",s["name"])
    return nStamps

def getAudience(notes):
    # see all audience codes: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:audience&fl=*&wt=xml
    # default audience
    audienceFlag = notes.get('audience',DEFAULT_AUDIENCE)
    if str(audienceFlag).lower() == 'international':
        audienceFlag = '2'
    elif str(audienceFlag).lower() == 'national':
        audienceFlag = '3'
    if str(audienceFlag) != '1' and str(audienceFlag) != '2' and str(audienceFlag) != '3':
        Logger.warning("Unknown audience: force default")
        audienceFlag = DEFAULT_AUDIENCE
    return audienceFlag

def getInvited(notes):
    # see all invited codes: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:invitedCommunication&fl=*&wt=xml
    # default invited
    invitedFlag = notes.get('invited',DEFAULT_INVITED)
    if str(invitedFlag).lower() == 'oui':
        invitedFlag = '1'
    elif str(invitedFlag).lower() == 'non':
        invitedFlag = '0'
    if str(invitedFlag) != '0' and str(invitedFlag) != '1':
        Logger.warning("Unknown invited: force default")
        invitedFlag = DEFAULT_INVITED
    return invitedFlag

def getPopular(notes):
    # see all popular levels codes: hhttps://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:popularLevel&fl=*&wt=xml
    # default pouplar level
    popFlag = notes.get('invited',DEFAULT_POPULAR)
    if str(popFlag).lower() == 'oui':
        popFlag = '1'
    elif str(popFlag).lower() == 'non':
        popFlag = '0'
    if str(popFlag) != '0' and str(popFlag) != '1':
        Logger.warning("Unknown popular level: force default")
        popFlag = DEFAULT_POPULAR
    return popFlag

def getPeer(notes):
    # see all peer reviewing codes: hhttps://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:popularLevel&fl=*&wt=xml
    # default peer reviewing
    peerFlag = notes.get('invited',DEFAULT_PEER)
    if str(peerFlag).lower() == 'oui':
        peerFlag = '1'
    elif str(peerFlag).lower() == 'non':
        peerFlag = '0'
    if str(peerFlag) != '0' and str(peerFlag) != '1':
        Logger.warning("Unknown peer reviewing type: force default")
        peerFlag = DEFAULT_PEER
    return peerFlag

def getProceedings(notes):
    # see all peer reviewing codes: https://api-preprod.archives-ouvertes.fr/ref/metadataList/?q=metaName_s:proceedings&fl=*&wt=xml
    # default proceedings
    proFlag = notes.get('invited',DEFAULT_PROCEEDINGS)
    if str(proFlag).lower() == 'oui':
        proFlag = '1'
    elif str(proFlag).lower() == 'non':
        proFlag = '0'
    if str(proFlag) != '0' and str(proFlag) != '1':
        Logger.warning("Unknown proceedings status: force default")
        proFlag = DEFAULT_PROCEEDINGS
    return proFlag

def setNotes(inTree,notes):
    nNotes = list()
    if type(notes) is not list:
        list_notes = [notes]
    else:
        list_notes = notes
    # define audience
    nNotes.append(etree.SubElement(inTree, "note"))
    nNotes[-1].set("type","audience")
    nNotes[-1].set("n",getAudience(list_notes))
    # define invited
    nNotes.append(etree.SubElement(inTree, "note"))
    nNotes[-1].set("type","invited")
    nNotes[-1].set("n",getInvited(list_notes))
    # define popular
    nNotes.append(etree.SubElement(inTree, "note"))
    nNotes[-1].set("type","popular")
    nNotes[-1].set("n",getPopular(list_notes))
    # define peer
    nNotes.append(etree.SubElement(inTree, "note"))
    nNotes[-1].set("type","peer")
    nNotes[-1].set("n",getPeer(list_notes))
    # define proceedings
    nNotes.append(etree.SubElement(inTree, "note"))
    nNotes[-1].set("type","proceedings")
    nNotes[-1].set("n",getProceedings(list_notes))
    
    for n in list_notes:
        if "comment" in n:
            nNotes.append(etree.SubElement(inTree, "note"))
            nNotes[-1].set("type","commentary")
            nNotes[-1].text = n["comment"]
        if "description" in n:
            nNotes.append(etree.SubElement(inTree, "note"))
            nNotes[-1].set("type","description")
            nNotes[-1].text = n["description"]
            
    return nNotes

def setAbstract(inTree,abstract):
