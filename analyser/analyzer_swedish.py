import libhfst
import os
import re
#from .analyzer_helper import check_capitalization
from .analyzer_base import BaseAnalyzer

class SwedishAnalyzer(BaseAnalyzer):

    def __init__(self, lang, analyzer_file):
        super().__init__(lang, analyzer_file)
        
    def lookup(self, word, **kwargs):
        result = super().lookup(word, **kwargs)
        return result

    


