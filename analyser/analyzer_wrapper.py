# -*- coding: utf-8 -*-
import os
from .analyzer_finnish import FinnishAnalyzer
from .analyzer_russian import RussianAnalyzer
from .analyzer_german import GermanAnalyzer
from .analyzer_swedish import SwedishAnalyzer
from .analyzer_base import BaseAnalyzer
from .analyser_apertium import ApertiumAnalyser
#from .other_analyser import OtherAnalyser

from .analyzers_config import *

def Analyzer(lang):
    '''
    A wrapper for different language analysers.
    
    Analysers should always have a lookup method which takes
    a single word as an input and returns a morphological
    analysis of said word in dictionary format, with the
    following fields:
    
    "base" : The lemma form.
    "pos" : The part-of-speech.
    "tags" : A list of all morphological tags.
    
    If you wish to add more functionality to a particular
    analyser, you may use the optional keyword arguments.
    '''

    analyser = None
    PREFIX = os.environ.get('ANALYZER_HOME', '/cs/puls/home/tkt_plus/revita/analyzers')
    analyzer_file = str(PREFIX + ANALYZER_FILE_PATH[lang][0])
    if lang in LANG_TO_ANALYZER:
        analyser = LANG_TO_ANALYZER[lang](lang, analyzer_file)
    else:
        raise NotImplementedError('No analyzer for ' + lang)

    return analyser


LANG_TO_ANALYZER = {
    'Finnish': FinnishAnalyzer,
    'Russian': RussianAnalyzer,
    'German': GermanAnalyzer,

    # 'Swedish': SwedishAnalyzer,
    'Swedish': ApertiumAnalyser,
    'Spanish': ApertiumAnalyser,
    'Catalan': ApertiumAnalyser,
    'French': ApertiumAnalyser,
    'Italian': ApertiumAnalyser,
    'Nanai': ApertiumAnalyser,
    
    'Erzya': BaseAnalyzer,
    'Meadow-Mari': BaseAnalyzer,
    'Komi-Zyrian': BaseAnalyzer,
    'North-Saami': BaseAnalyzer,
    'Udmurt': BaseAnalyzer,
    'Kazakh': BaseAnalyzer,
    'Sakha': BaseAnalyzer
    }


ANALYZER_FILE_PATH = {
    'Russian':      ('/ru/CrosslatorTagger/russian.vcb',   'crosslator'),
    'Udmurt':       ('/udm/src/analyser-gt-desc.hfstol',   'giella'),
    'Finnish':      ('/fin/src/analyser-gt-desc.hfstol',   'giella'),
    'Erzya':        ('/myv/src/analyser-gt-desc.hfstol',   'giella'),
    'Meadow-Mari':  ('/mhr/src/analyser-gt-desc.hfstol',   'giella'),
    'Komi-Zyrian':  ('/kpv/src/analyser-gt-desc.hfstol',   'giella'),
    'German':       ('/de/invopt.hfst.ol', 'zmorge'),
    'North-Saami':  ('/sme/src/analyser-gt-desc.hfstol',   'giella'),
    # 'Swedish':      ('/sv/sv-analysis.hfst.ol',            'sv'),
    'Komi-Permiak': ('None',                               'None'),
    'Kazakh':       ('/apertium-kaz/kaz.automorf.hfst',    'kaz'),
    'Sakha':        ('/apertium-sah-enhancement/sah.automorf.hfst',   'sah'),
    'Swedish':      ('/apertium-swe/swe.automorf.hfstol', 'apertium'),
    'Spanish':      ('/apertium-spa/spa.automorf.hfstol', 'apertium'),
    'Catalan':      ('/apertium-cat/cat.automorf.hfstol', 'apertium'),
    'French':       ('/apertium-fra/fra.automorf.hfstol', 'apertium'),
    'Italian':      ('/apertium-ita/ita.automorf.hfstol', 'apertium'),
    'Nanai':        ('/apertium-gld/gld.automorf.hfstol', 'apertium'),
    }

