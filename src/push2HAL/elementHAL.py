####*****************************************************************************************
####*****************************************************************************************
####*****************************************************************************************
#### Library part of push2HAL
#### Copyright - 2024 - Luc Laurent (luc.laurent@lecnam.net)
####
#### description available on https://github.com/luclaurent/push2HAL
####*****************************************************************************************
####*****************************************************************************************

from abc import ABC, abstractmethod
from loguru import logger


## create a custom logger
logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> |"
    "<red>PUSH2HAL</red> |"
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra[ip]} {extra[user]} - <level>{message}</level>"
)

## see on references folder
## and https://github.com/CCSDForge/HAL/blob/master/schema/Readme.md


class HALelt(ABC):
    
    def __init__(self, data=None):
        self.data = None
        self.dataJSON = None
        self.dataXML = None
        self.dataHAL
        
        ## load data
        if data is not None:
            self.loadData(data)
    
    def loadData(self, data):
    
    def populate(self, data):
    
    def writeJSON(self, filename):
    
    def writeXML(self, filename):
    

class Article(HALelt):
    
class Book(HALelt):

class BookChapter(HALelt):

class BookReview(HALelt):

class DataPaper(HALelt):
    
class Poster(HALelt):

class Proceedings(HALelt):
    
class Manual(HALelt):
    
class Critique(HALelt):
    
class SynthWork(HALelt):
    
class Dictionary(HALelt):
    
class Blog(HALelt):
    
class Dataset(HALelt):
    
class Software(HALelt):
    
class Notice(HALelt):
    
class Translation(HALelt):
    
class Undefined(HALelt):
    
class PrePrint(HALelt):
    
class ReportChapter(HALelt):
    
class ResearchReport(HALelt):
    
class TechnicalReport(HALelt):
    
class TechnicalReport(HALelt):
    
class Conference(HALelt):
    
class Patent(HALelt):
    
class Report(HALelt):
    
class Thesis(HALelt):
    
class HDR(HALelt):
    
class PhDThesis(HALelt):
    
class MasterThesis(HALelt):
    
class Image(HALelt):
    
class Photography(HALelt):
    
class Drawing(HALelt):
    
class Illustration(HALelt):
    
class Engraving(HALelt):
    
class Graphics(HALelt):
    
class Video(HALelt):
    
class Sound(HALelt):
    
class DocConf(HALelt):
    
class MasterThesis(HALelt):
    
class Note(HALelt):
    
class ActivityReport(HALelt):
    
class Synthesis(HALelt):
    
class Other(HALelt):
