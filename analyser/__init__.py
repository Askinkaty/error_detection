# -*- coding: utf-8 -*-
'''
A generic parsing error, so that we can ignore
words which cannot be parsed.
'''

import sys
import os
# Add language-tools to path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
#TODO: was ParsingError
class AnalysisError(Exception):
    pass

from .analyzer_wrapper import Analyzer

# Fix spelling
def Analyser(lang):
    analyser = Analyzer(lang)
    analyser.analyse = analyser.analyze
    return analyser
