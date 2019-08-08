# -*- coding: utf-8 -*-

import os, sys, re, string, copy
import itertools
from . import AnalysisError
from .analyzer_base import BaseAnalyzer
from .analyzers_config import *
# Already applied in analyser_base
# from .character_map import characters_map
# from .read_rules import *
PREFIX = os.environ.get('ANALYZER_HOME', '/cs/puls/home/tkt_plus/revita/analyzers')
analyser_file = PREFIX + '/ru/CrosslatorTagger/russian.vcb'
crosslator_path = PREFIX + '/ru/CrosslatorTagger/python'
import pymorphy2
sys.path.append(crosslator_path)
try:
    from CrosslatorTagger import Analyzer
except ImportError:
    print("CrosslatorTagger is not imported")


bad_lemmas = (
    # illegal lemmas
    'дети',
    'люди',
    'сталенький',
    'свое',
    'тем',
    'того',
    'выша',
    'пра',         # 'пре', ...

    # legal, but far too rare or archaic
    'мень',        # меня, менем: exists in Dahl's dictionary
    'пря',         # competition
    'придти',      # пришел, ...

    # TODO: should watch that these are Capitalized
    'ир',          # Ира, Иру ...
    'котор',       # Котор = city in Montenegro
    'коты',        # (legal but too rare) kind of fur-based women's footware 
)

# do not use.  use banned_lemmas_for_surface BELOW.
bad_surfaces = (
    ## 'Маша',      # махать
    ## 'Паша'       # пахать
)

banned_lemmas_for_surface = {
    'тем': ['тьма'],
    # 'при': ['пря'],
    'второй': ['втора'], # (legal but too rare)
    'котов': ['котов'],

    # TODO: should watch that these are Capitalized
    'Маша': ['махать'],
    'Паша': ['пахать'],
    'лет': ['лета'],     # keeps analysis for лёт
}

# Predic is used for words like надо, можно...
bad_tags = (
    'idiom',
    # 'Predic'
)

# Not used as of 2018-09-26
pos_list = [
    'Noun',
    'Verb',
    'Adj',
    'Pron',
    'Num',
    'Adv',
    'Interj',
    'Conj',
    'PostP',
    'Prep',
    'Parenthetic',
    'Particle',
    'Punct'
]

class SingleParsing:
    def __init__(self, word_str):
        tokens = word_str.split(';')
        #print('TOKENS: *** {0}'.format(tokens))
        if len(tokens) < 2:
            raise AnalysisError()

        else:
            self.lemma = tokens[0].lower()
            self.pos = tokens[1]
            self.tags = tokens[2:]
            self.hash_str = self.lemma + self.pos
            for tag in sorted(self.tags):
                self.hash_str += tag

    def to_serial(self):
        if self.tags:
            return '{}+{}+{}'.format(
                self.lemma.replace('-',''),
                self.pos,
                '+'.join(self.tags)
            )
        else:
            return '{}+{}'.format(
                self.lemma.replace('-',''),
                self.pos
            )

    def contains(self, *tags):
        all_tags = set()
        all_tags.add(self.pos)
        if len(self.tags) > 0:
            tgs = self.tags.values()
            for t in tgs:
                all_tags.add(t)
        result = True
        for i in tags:
            result = result and i in all_tags
        return result

    def all_tags(self):
        return self.tags + [self.pos]

    def modify_pos(self):
        pos_map = analyzer_to_POS_map['crosslator']
        pos = pos_map.get(self.pos, self.pos)
        self.pos = pos

        #function for modification Crosslator Tagger output
    def modify_tags(self):
        new_tags = dict()
        tags = [el.split('=') for el in self.tags[0].split(',')]
        for tag in tags:
            if self.pos in ['Noun', 'Adj', 'Pron', 'Num', 'Verb', 'Participle']:
                key = tag[0].upper()
                value = ''
                if tag[0] in ['animate', 'gender', 'number', 'person']:
                    value = tag[1].capitalize()
                if tag[0] == 'case':
                    case_map = {
                        '0': '0',
                        'i': 'Nom',
                        'r': 'Gen',
                        'v': 'Acc',
                        'd': 'Dat',
                        't': 'Ins',
                        'p': 'Loc'
                    }
                    value = case_map.get(tag[1], '0')
                if tag[0] == 'comp':
                    comp_map = {'0': '0',
                                'com': 'Comp',
                                'pos': 'Positive',
                                'sup': 'Super'}
                    value = comp_map.get(tag[1], '0')
                    kay = 'COMPAR'
                if tag[0] == 'short':
                    form_map = {'y': 'short', 'n': 'full'}
                    value = form_map.get(tag[1], '0')
                if tag[0] in ['aspect', 'mood', 'tense', 'transit', 'voice', 'inf']:
                    verb_map = {
                        '0': '0',
                        'sov': 'Perf',
                        'nesov': 'Imperf',
                        'imp': 'Imprt',
                        'ind': 'Ind',
                        'past': 'Past',
                        'pres': 'Pres',
                        'fut': 'Fut',
                        'tr': 'Trans',
                        'intr': 'Intrans',
                        'a': 'Act',
                        'p': 'Pass',
                        'n': 'Non-infinit',
                        'y': 'Infinit'
                    }
                    value = verb_map.get(tag[1], '0')
                if len(key) != 0:
                    new_tags[key] = value
        self.tags = new_tags

    def __eq__(self, other):
        return (
            self.lemma == other.lemma
            and self.pos == other.pos
            and set(self.tags) == set(other.tags)
        )

    def __hash__(self):
        return hash(self.hash_str)

    def __repr__(self):
        return str((self.lemma, self.pos, self.tags))



class WordParsings:
    def __init__(self, surface, parse_strs, morph, next_word):
        self.surface = surface
        self.parsings = []
        self.lemmas = set()
        self.morph = morph
        parse_strs = parse_strs.split('|')
        for parse_str in parse_strs:
            try:
                wp = SingleParsing(parse_str)
                wp.modify_pos()
                wp.modify_tags()
                self.parsings.append(wp)
                self.lemmas.add(wp.lemma)
            except AnalysisError:
                continue

    def __repr__(self):
        string = 'Parsings for {}:'.format(self.surface)
        for p in self.parsings:
            string += str(p)
        string += '\nLemmas = {}'.format(str(self.lemmas))
        return string

    def to_dict(self):
        retv = []
        # retv = {}
        # retv['analyses'] = {}
        # retv['surface'] = self.surface
        # retv['analyses']['Russian'] = []
        for p in self.parsings:
            reading = []
            #print(p)
            dct = {}
            if hasattr(p, 'pclemma'):
                dct['base-participle'] = p.pclemma
            dct['base'] = p.lemma
            dct['pos'] = p.pos
            dct['tags'] = p.tags
            reading.append(dct)
            # retv['analyses']['Russian'].append(reading)
            retv.append(reading)
        return retv

    def contains(self, *tags):
        result = True
        for t in tags:
            tr = False
            for p in self.parsings:
                tr = p.contains(t)
                if tr:
                    break
            result = result and tr
            if not result:
                break
        return result

    def remove_if(self, *tags):
        good = {
            p
            for p in self.parsings
            if not p.contains(*tags)
        }
        new_parsing = []
        for g in good:
            new_parsing.append(g)
        self.parsings = new_parsing

    def remove_with_lemma(self, lemma):
        good = {
            p
            for p in self.parsings
            if p.lemma != lemma
        }
        new_parsing = []
        new_lemmas = set()
        for g in good:
            new_parsing.append(g)
            new_lemmas.add(g.lemma)
        self.parsings = new_parsing
        self.lemmas = new_lemmas

    def lemmas_with(self, *tags):
        result = {
            p
            for p in self.parsings
            if p.contains(*tags)
        }
        if len(result) != 0:
            return result
        else:
            return None

    def tags_for_lemma(self, lemma):
        tags = []
        for p in self.parsings:
            if p.lemma == lemma:
                tags.append(p.tags)
        if len(tags) != 0:
            return tags
        else:
            return None

    def to_serial(self):
        #print(self.parsings)
        parsings_s = (_.to_serial() for _ in self.parsings)
        return '{}|{}|{}'.format(
            self.surface,
            '#'.join(self.lemmas),
            '|'.join(parsings_s)
        )

    def to_vector(self):
        poses = {
            wp.pos
            for wp in self.parsings        }
        return [
            1 if pos in poses
            else 0
            for pos in pos_list
        ]

    def modify_output(self):
        for parsing in self.parsings:
            try:
                parsing.modify_pos()
                parsing.modify_tags()
            except AnalysisError:
                continue

    def is_ambiguous(self):
        return len(self.lemmas) > 1

    #Remove all analyses if the lemma is bad
    def _remove_bad_lemmas(self):
        if self.is_ambiguous():
            #self.lemmas.difference_update(bad_lemmas)
            for lemma in self.lemmas:
                if lemma in bad_lemmas:
                    self.remove_with_lemma(lemma)
        else:
            if self.lemmas.intersection(bad_lemmas):
                #print(self.lemmas.intersection(bad_lemmas))
                self.lemmas = set()
                self.parsings = []

    #empty analyses is the surface in the bad list
    def _remove_bad_surfaces(self):
        if self.surface in bad_surfaces:
            self.parsings = []
            self.lemmas = set()

    def _remove_with_tag(self, *tags):
        new_parsings = []
        new_lemmas = set()
        for parsing in self.parsings:
            if not parsing.contains(*tags):
                new_parsings.append(parsing)
                new_lemmas.add(parsing.lemma)
        self.lemmas = new_lemmas
        self.parsings = new_parsings

    def _remove_bad_tags(self):
        for t in bad_tags:
            self._remove_with_tag(t)

    # def _remove_same_lemmas(self):
    #     char_map = characters_map['Russian']
    #     for lemma in self.lemmas:
    #         for key, value in char_map.items():
    #             if key in lemma:
    #                 new_lemma = lemma.replace(key, value)
    #                 if new_lemma in self.lemmas:
    #                     self.remove_with_lemma(lemma)

    def _remove_lemmas_for_surface(self):
        if self.surface in banned_lemmas_for_surface:
            for word in banned_lemmas_for_surface[self.surface]:
                self.remove_with_lemma(word)

    def _modify_participles(self):
        """
        Function to replace verb base of a participle with a patriciple base
        using morphological generator
        """
        # char_map = characters_map['Russian'] #pymorphy2 uses ё but not Crosslator
        new_parsings = []
        for parsing in self.parsings:
            if parsing.pos == 'Participle':
                ps = self.morph.parse(self.surface)
                chosen_p = [p for p in ps if p.tag.POS in ['PRTF', 'PRTS']]
                if not chosen_p:
                    return None
                else:
                    chosen_p = chosen_p[0]
                    inflected = chosen_p.inflect({'nomn', 'sing', 'masc'})
                    lemma = inflected.word
                    # for key, value in char_map.items():
                    #     if key in lemma:
                    #         lemma = lemma.replace(key, value)
                    parsing.pclemma = lemma
                    new_parsings.append(parsing)
            else:
                new_parsings.append(parsing)
        self.parsings = new_parsings
        return True        
                        
    def _resolve_participles(self):
        """
        Function to replace a verb base by an adjective base
        if there are both of the analyses for a parsitiple
        """
        posses = set(parsing.pos for parsing in self.parsings)
        new_parsings = []
        new_lemmas = set()
        if 'Participle' in posses and 'Adj' in posses:
            combinations = itertools.combinations(self.parsings, 2)
            for c in combinations:
                pair_posses = []
                for el in c:
                    pair_posses.append(el.pos)
                if 'Participle' in pair_posses and 'Adj' in pair_posses:
                    try:
                        if c[0].tags['GENDER'] == c[1].tags['GENDER'] and \
                           c[0].tags['NUMBER'] == c[1].tags['NUMBER'] and \
                           c[0].tags['CASE'] == c[1].tags['CASE']:
                            base = None
                            for pair in c:
                                if pair.pos == 'Adj':
                                    base = pair.lemma
                                    new_lemmas.add(base)
                            for pr in c:
                                if pr.pos == 'Participle':
                                    if base != None:
                                        pr.lemma = base
                                new_parsings.append(pr)
                    except Exception as ex:
                        print(ex)
            for prsg in self.parsings:
                if prsg.pos != 'Participle' and prsg.pos != 'Adj':
                    new_parsings.append(prsg)
                    new_lemmas.add(prsg.lemma)
            if new_parsings and new_lemmas:
                self.parsings = new_parsings
                self.lemmas = new_lemmas

    def _analysis_extention(self):
        new_parsings = []
        for parsing in self.parsings:
            if parsing.pos == 'Adj':
                if 'GENDER' in parsing.tags and parsing.tags['GENDER'] == '0':
                    for g in ['F', 'N', 'M']:
                        new_parsing = copy.deepcopy(parsing)
                        new_parsing.tags['GENDER'] = g
                        new_parsings.append(new_parsing)
                else:
                    new_parsings.append(parsing)
            else:
                new_parsings.append(parsing)
        #print('_________________________', new_parsings)
        self.parsings = new_parsings

    # def _government_analysis_extention(self):
    #     _, government_rules = choose_rules('Russian')
    #     government_rules = get_all_rules(government_rules)
    #     bases = set(parsing.lemma for parsing in self.parsings)
    #     posses = set(parsing.pos for parsing in self.parsings)
    #     result = []
    #     for b in bases:
    #         all_chosen_rules = [rule[0]
    #                             for rule in government_rules
    #                             if b==rule[0]['LEMMA']]
    #         rule_posses = set(rule[0]['POS']
    #                           for rule in government_rules
    #                           if b==rule[0]['LEMMA'])
    #         if len(all_chosen_rules) != 0:
    #             N = len(all_chosen_rules)
    #         else:
    #             continue
    #         new_analyses = []
    #         for item in self.parsings:
    #             if item.pos in rule_posses:
    #                 for i in range(N):
    #                     new_analyses.append(item)
    #             else:
    #                 new_analyses.append(item)
    #         chosen_analyses = [a
    #                            for a in new_analyses
    #                            if a.pos in rule_posses]
    #         if len(chosen_analyses) == len(all_chosen_rules):
    #             for rule, analysis in zip(all_chosen_rules, chosen_analyses):
    #                 new_analysis = copy.deepcopy(analysis)
    #                 if analysis.pos == rule['POS']:
    #                     for k, v in list(rule.items()):
    #                         if k not in ['POS', 'LEMMA']:
    #                             new_analysis.tags[k] = v
    #                 result.append(new_analysis)
    #         elif len(chosen_analyses) != len(all_chosen_rules):
    #             for ch_a in chosen_analyses:
    #                 result.append(ch_a)
    #         if any(rule_posses.difference(posses)):
    #             for ch_r in all_chosen_rules:
    #                 if ch_r['POS'] not in posses:
    #                     new_analysis_addition = copy.deepcopy(self.parsings[0])
    #                     new_analysis_addition.lemma = b
    #                     new_analysis_addition.pos = ch_r['POS']
    #                     new_analysis_addition.tags = dict()
    #                     for ch_r_k, ch_r_v in list(ch_r.items()):
    #                         if ch_r_k not in ['POS', 'LEMMA']:
    #                             new_analysis_addition.tags[ch_r_k] = ch_r_v
    #                     result.append(new_analysis_addition)
    #         rest = [a
    #                 for a in new_analyses
    #                 if a.pos not in rule_posses]
    #         for el in rest:
    #             result.append(el)
    #     if len(result) != 0:
    #         self.parsings = result

    def cleanup(self):
        self._remove_bad_surfaces()
        self._remove_bad_tags()
        self._remove_bad_lemmas()
        # self._remove_same_lemmas()
        self._remove_lemmas_for_surface()
        mp = self._modify_participles()
        if not mp:
            self._resolve_participles()
        self._analysis_extention()
        # self._government_analysis_extention()

class RussianAnalyzer(BaseAnalyzer):
    def __init__(self, lang, analyzer_file):
        self.language = lang
        self.analyser = Analyzer()
        self.analyser.loadVocabulary(analyzer_file)
        self.morph = pymorphy2.MorphAnalyzer()

        
    def lookup(self, word, next_word=None, **kwargs):
        word = self._filter_by_next_word(word, next_word)
        # word = self._character_mapping(word)
        if word is not None:
            raw_strs = self.analyser.analysis(word)
            #print('RAW: **** {0}'.format(raw_strs))
            #print('WORD: ****** {0}'.format(word))
            wp = WordParsings(word, raw_strs, self.morph, next_word=next_word)
            #print(wp)
            wp.cleanup()
            #print(wp)

            #print(wp.to_serial())
            #print(wp)
            #wp.modify_output()
            #print(wp)
            #print('___________________________')
            return wp.to_dict()

    # def analyze(self, word, lemmas = False, first = False, next_word = False):
    #     result = self.lookup(word, lemmas, first, next_word)
    #     return self.format_sort(result)


    def _filter_by_next_word(self, word, next_word):
        if len(word) == 1 and next_word in ['.', ')', ']']:
            return None
        else:
            return word

    # def _character_mapping(self, word):
    #     """
    #     A function to map one characters to others before analyses.
    #     """
    #     if word is not None:
    #         ch_map = characters_map.get('Russian', None)
    #         if ch_map is not None:
    #             for k in list(ch_map.keys()):
    #                 word = word.replace(k, ch_map[k])
    #         return word
    #     return word
