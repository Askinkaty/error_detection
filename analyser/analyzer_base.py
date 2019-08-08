# -*- coding: utf-8 -*-
import copy
import re
import libhfst

from .analyzers_config import *
from .pre_analyze_config import *
from .data_to_filter import *
from .compound_parser import *

import rules

class BaseAnalyzer:
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

    def __init__(self, lang, analyzer_file):
        self.language = lang
        self.analyzer = libhfst.HfstInputStream(analyzer_file).read()


    def analyze(self, word, names=True, **kwargs):
        '''
        This is the function to be called for analyzing a word.
        For extending the BaseAnalyzer try to use as many 
        superclass methods as possible.
        '''
        word = self.pre_analyzer(word, **kwargs)
        result = self.lookup(word, **kwargs)
        result = self.post_analyzer(result, word, **kwargs)
        return result


    def pre_analyzer(self, word, next_word='', **kwargs):
        """
        A function to preprocess an analyzer's input.
        """
        
        word = self.filter_by_next_word(word, next_word)
        word = self.character_mapping(word)
        word = self.check_capitalization(word, 'surface')
        
        return word


    def lookup(self, word, **kwargs):        
        analyses = self.analyzer.lookup(word, output='raw')
        analyses = self.analyses_to_string(analyses)
        result = self.parse_analysis(analyses)
        return result


    def post_analyzer(self, lkp_result, word, **kwargs):
        result = self.process_non_analyzable(word, lkp_result)
        result = self.to_dict(lkp_result, word)
        result = self.format_sort(result, **kwargs)
        if result['analyses'][self.language] == [{}]:
            result['analyses'][self.language] = []
        govrules = rules.government_rules.get(self.language, {})
        analyses = result['analyses'][self.language]
        exts = []
        dels = set()
        if govrules:
            for i, analysis in enumerate(analyses):
                a = analysis[0]
                (lemma, pos) = (a['base'], a['pos'])
                key = (lemma, pos)
                if key in govrules:
                    dels.add(i)
                    cases = govrules[key]
                    ext = []
                    for case in cases:
                        e = copy.deepcopy(a)
                        e['tags']['GOV_CASE'] = case
                        ext.append([e])
                    exts.extend(ext)
            analyses = [
                a
                for i, a in enumerate(analyses)
                if i not in dels
            ]
            analyses.extend(exts)
            result['analyses'][self.language] = analyses
        return result


    def format_sort_old(self, result, **kwargs):
        '''Sort the analyses by fragment count'''
        sorted_result = []
        analyses_by_length = {}
        longest = 0
        for analysis in result[self.language]['analyses']:
            count = analysis['base'].count('+')
            if count not in analyses_by_length:
                analyses_by_length[count] = []
            if longest < count:
                longest = count
            analyses_by_length[count].append(analysis)
        for analyses in analyses_by_length:
            for a in analyses_by_length[analyses]:
                sorted_result.append(a)
        result[self.language]['analyses'] = sorted_result
        return result

    def format_sort(self, result, **kwargs):
        """ Sort readings by length """
        analyses = result['analyses'][self.language]
        #print(analyses)
        result['analyses'][self.language] = sorted(analyses, key=len)
        return result


    def check_capitalization(self, token, schema):
        """
        A function which decides depending on language whether to keep word case as it was
        in an input or to change it.
        """
        if schema == 'surface':
            capitalization_schema = language_to_capitalization_map[self.language]
        else:
            capitalization_schema = base_capitalization_map[self.language]
        if capitalization_schema == 'default':
            return token
        elif capitalization_schema == 'lower':
            #print(token)
            return token.lower()
        elif capitalization_schema == 'upper':
            return token.capitalize()
        else:
            return token


    def character_mapping(self, word):
        """
        A function to map one characters to others before analyses.
        """
        if word != None:
            ch_map = characters_map.get(self.language, None)
            if ch_map != None:
                for k in list(ch_map.keys()):
                    word = word.replace(k, ch_map[k])
            return word
        else:
            return None


    def filter_by_next_word(self, word, next_word):
        return word


    def analyses_to_string(self, analyses):
        """
        A function to change the form of the output from a list of char into
        a string
        Args:
          analyses: lololkek 
        """
        pattern = re.compile(r'^@.*@$')
                    
        output_format = output_format_map.get(self.language, None)
        if output_format == 'default':
            result = []
            if len(analyses) > 0:
                for analysis in analyses:
                    analysis_string = ''
                    for element in analysis[1]:
                        if not pattern.match(element):
                            analysis_string += element
                    result.append(analysis_string)
            else:
                result = analyses
        else:
            result = analyses
        return result 


    def parse_analysis(self, analyses):
        analyzer_type = language_to_analyzer_type.get(self.language, language_to_analyzer_type['DEFAULT'])
        pos_map = analyzer_to_POS_map[analyzer_type]
        result = []
        analyses_input = []
        if len(analyses) > 0:
            for s in analyses:
                morph_data, is_compound = self.parse_compound(s)
                base = ''
                pos = ''
                tags = None
                reading = []
                for el in morph_data:
                    if len(el) != 0:
                        base_part = self.check_capitalization(el[0], 'base')
                        base = base_part
                        if len(el) > 1: 
                            pos = el[1]
                            if len(el) > 2:
                                tags = el[2:]
                    base = base.lstrip('+')
                    base = self.process_base(base)
                    base = self.check_capitalization(base, 'base')
                    pos = pos.replace('.', '%')
                    new_pos = pos_map.get(pos, pos)
                    new_tags = self.modify_tags(tags)
                    element = {'pos': new_pos, 'base': base, 'tags': new_tags}
                    reading.append(element)
                result.append(reading)
                assert isinstance(new_tags, dict)
                #result = self.choose_base(element, result)

        else:
            empty_result = {}
            result.append(empty_result)
        return result


    def parse_compound(self, potential_compound):
        """
        The CompoundParser class has language specific compound parsing
        methods. Edit that accordingly.
        """
        return CompoundParser(self.language).parse_compound(potential_compound)
        

    def process_base(self, base):
        s = re.findall(r"@(\w+)+", base) # clean base forms from gram. tags from Finnish bases
        if len(s) != 0:
            return max(s, key=len)
        else:
            return base

    
        
    def choose_base(self, analysis, result):
        """
        A function to choose among options like the following:
        {'pos': 'Noun', 'base': 'suku+nimi', 'tags': {'CASE': 'Gen', 'NUMBER': 'Sg'}}
        {'pos': 'Noun', 'base': 'sukunimi', 'tags': {'CASE': 'Gen', 'NUMBER': 'Sg'}}
        We choose the option with minimal number of stems (plusses) if tags are
        identical.
        """
        base = analysis['base'].replace('+', '')
        tags = analysis['tags']
        if len(result) != 0:
            for el in result:
                if (base == el['base'].replace('+', '')
                and tags == el['tags'] and el['pos'] == analysis['pos']):
                    if el['base'].count('+') > analysis['base'].count('+'):
                        result.remove(el)
                        result.append(analysis)
                    else:
                        continue
                else:
                    if analysis not in result:
                        result.append(analysis)
        else:
            result.append(analysis)
            
        return result

    
    def modify_tags(self, tags):
        tag_map = language_to_tag_map.get(self.language, language_to_tag_map['DEFAULT'])
        ##- print('*** TAG MAP: %s' % tag_map)
        new_tags = dict()
        if tags != None:
            if len(tags) != 0:
                for tag in tags:
                    key = tag_map.get(tag, 'UNKNOWN')
                    new_tags[key] = tag
        return new_tags


    def process_non_analyzable(self, token, token_dict):
        new_token_dicts = []
        whitespace_flag = False
        for analysis in token_dict:
            if re.match(r'\d', token):
                analysis = {}
                analysis['pos'] = 'number'
            if not re.match(r'(?u)\w+', token):
                analysis = {}
                if re.match(r'\s', token):
                    analysis['pos'] = 'whitespace'
                    whitespace_flag = True
                else:
                    analysis['pos'] = 'Punct'
                    #print(analysis)
            if '-' in token:
                analysis = {}
                analysis['pos'] = 'Hyphened' #hyphenated
            new_token_dicts.append(analysis)
        return new_token_dicts


    def add_base(self, analyses):
        bases = set()
        for analysis in analyses:
            if 'base' in analysis:
                base = analysis['base'].lower()
                base_parts = base.split('+')
                for part in base_parts:
                    bases.add(part)
        return bases

    def to_dict(self, analyses, word):
        d = {'analyses': {self.language: analyses},
             'surface': word}
        return d
        
