import libhfst
from pprint import pprint
import re
from .analyzer_base import BaseAnalyzer
BLACKLISTED_FIRSTS = ['E', 'Es']

class GermanAnalyzer(BaseAnalyzer):

    
    def __init__(self, lang, analyzer_file, **kwargs):
        self.language = lang
        self.analyzer = libhfst.HfstInputStream(analyzer_file).read()
        #self.__init_analyzer(analyzer_file)        


    # def __init_analyzer(self, analyzer_file):
    #     print(analyzer_file)
    #     command = 'fst-infl2 ' + str(analyzer_file)
    #     self.analyzer = pexpect.spawn(command, encoding='utf-8')
    #     self.analyzer.expect('finished.')

    def lookup(self, word, **kwargs):
        analyses = self.analyzer.lookup(word, output='raw')
        analyses = self.analyses_to_string(analyses)
        analyses = self.__cleanup_smorlemma_tags(analyses)
        result = self.parse_analysis(analyses)
        result = self.__fix_compound_pos(result)
        if result != [{}] and word != '':
            #result = self.__remove_empty_readings(result)
            result = self.__disambiguate_by_if_first(result, word, kwargs.get('first'))
        if kwargs.get('first'):
            result = self.__remove_blacklisted_firsts(result)
        if result == [{}]:
            result = []
        return result

    def __cleanup_smorlemma_tags(self, analyses, **kwargs):
        analyses = [self.__transformation(a) for a in analyses]
        return analyses

    def __remove_blacklisted_firsts(self, analyses):
        """ Function to remove analyses that are blacklisted in the first=True case"""
        new_analyses = []
        for r in analyses:
            reading = [a for a in r if a['base'] not in BLACKLISTED_FIRSTS]
            if reading != []:
                new_analyses.append(reading)
        return new_analyses


    def __fix_compound_pos(self, analyses):
        """ Fix empty pos in all but last part of compound"""
        for reading in analyses:
            for analysis in reading:
                if analysis['pos'] == '' and len(reading) >= 2:
                    analysis['pos'] = reading[-1]['pos']
        return analyses
        


    def __transformation(self, a):
        """ Do it """
        a = a.replace('<~>', '')
        a = a.replace('-<TRUNC>', '#')
        a = a.replace('{', '')
        a = a.replace('{', '')
        a = re.sub(r"<->[a-z]*", "", a)
        return a


    def __disambiguate_by_if_first(self, analyses, word, first):
        """ 
        Removes non noun analyses if not the first word
        in a sentence.
        """
        if not first and word[0].isupper():
            return self.__remove_non_noun_analyses(analyses)
        else:
            return analyses


    def __remove_non_noun_analyses(self, analyses):
        """ Remove non noun analyses"""
        analyses = [a for a in analyses if (a[0]['pos'] == 'Noun' or a[0]['pos'] == 'Prop')]
        return analyses


    def __remove_empty_readings(self, analyses):
        """ Title says it all"""
        new_analyses = []
        print(len(analyses))
        for r in analyses:
            reading = [a for a in r if a['pos'] != '']
            if reading != []:
                new_analyses.append(reading)
        print(len(new_analyses))
        return new_analyses
            
                
        
        



    """
    Vermittlung<->s<#>gespräch<+NN><Neut><Nom><Pl>
    Vermittlung<->s<#>gespräch<+NN><Neut><Gen><Pl>
    Vermittlung<->s<#>gespräch<+NN><Neut><Dat><Sg><Old>
    Vermittlung<->asd<s<#>gespräch<+NN><Neut><Acc><Pl>
    Vermittl<~>ungs<#>gespräch<+NN><Neut><Nom><Pl>
    Vermittl<~>ungs<#>gespräch<+NN><Neut><Gen><Pl>
    Vermittl<~>ungs<#>gespräch<+NN><Neut><Dat><Sg><Old>
    Vermittl<~>ungs<#>gespräch<+NN><Neut><Acc><Pl>


    """

