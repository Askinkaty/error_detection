# -*- coding: utf-8 -*-

import os
import re
import string

import libhfst

from . import AnalysisError
from .analyzer_base import BaseAnalyzer
from .analyzers_config import *
from .data_to_filter import *

PREFIX = os.environ.get(
    'ANALYZER_HOME', '/cs/puls/home/tkt_plus/revita/analyzers')
analyser_file = os.path.join(
    PREFIX, 'fin/src/analyser-gt-desc.hfstol')
generator_file = os.path.join(
    PREFIX, 'fin/src/generator-gt-desc.hfstol')


class FinnishAnalyzer(BaseAnalyzer):
    def __init__(self, lang, analyzer_file):
        super().__init__(lang, analyzer_file)

    def lookup(self, word, **kwargs):
        lookstr = word.lower() if word in lowercase else word
        if lookstr.lower() in fixed_analyses:
            ps = fixed_analyses[lookstr.lower()]
            wp = WordAnalyses(word, ps)
        else:
            raw_strs = self.analyzer.lookup(lookstr, output='tuple')
            # Filter out garbage analyses with no POS
            parse_strs = filter(
                lambda x: '+' in x,
                (t[0] for t in raw_strs)
            )
            clean_strs = [str_cleanup(_) for _ in parse_strs]
            wp = WordAnalyses(word, clean_strs)
            wp.cleanup()
        return wp.to_dict()


generator = None

def str_cleanup(s):
    # Remove all Use (except Rare, sub, Arch) and Sem tags
    pattern = r'\+(Use/(?!(Rare|sub|Arch))|Sem/)[a-zA-z]*'
    s = re.sub(re.compile(pattern), '', s)
    # Replace +Pass with +Pss, since they are equivalent
    s = s.replace('+Pass', '+Pss')
    # Same with +Propn and +Prop
    s = s.replace('+Propn', '+Prop')
    # Fix post-position POS
    s = s.replace('+Adp+Po', '+Po')
    # Typo
    s = s.replace('+Ni', '+N')
    # Why not
    s = s.replace('+CS', '+CC')
    # iffy as hell (EU-maat, b-juniori)
    s = s.replace('+N-', '+N#')
    return s


def generate(parse_str):
    '''
    Generate a word given a parser output (lemma + tags).
    '''
    global generator
    s = parse_str.replace('#', '+Use/NoHyphens#')
    if not generator:
        generator = libhfst.HfstInputStream(generator_file).read()
    g = generator.lookup(s, output='tuple')
    try:
        g = g[0][0]
        return g
    except IndexError:
        return s.split('+')[0]


class SingleAnalysis:
    '''
    A class representing a single possible analysis.
    '''
    def __init__(self, word_str):
        # Deal with '+', analysed as '++Punct' and stuff
        if word_str.startswith('+'):
            tokens = ['+'] + word_str[2:].split('+')
        else:
            tokens = word_str.split('+')
        if len(tokens) < 2:
            raise AnalysisError()
        else:
            self.lemma = tokens[0]
            self.pos = tokens[1]
            self.tags = tokens[2:]
            self.hash_str = self.lemma + self.pos
            for tag in sorted(self.tags):
                self.hash_str += tag

    def to_serial(self):
        if self.tags:
            return '{}+{}+{}'.format(
                self.lemma.replace('-', ''),
                self.pos,
                '+'.join(self.tags)
            )
        else:
            return '{}+{}'.format(
                self.lemma.replace('-', ''),
                self.pos
            )

    def all_tags(self):
        return self.tags + [self.pos]

    def has_tag(self, tag):
        return tag in self.tags

    def has_pos(self, pos):
        return pos == self.pos

    def __eq__(self, other):
        return (
            self.lemma == other.lemma
            and self.pos == other.pos
            and set(self.tags) == set(other.tags)
        )

    def __hash__(self):
        return hash(self.hash_str)

    def __str__(self):
        return str((self.lemma, self.pos, self.tags))


class CompoundAnalysis:
    '''
    Wrapper for compound words.
    '''
    def __init__(self, parse_str):
        self.analysis_list = []
        for word_str in parse_str.split('#'):
            try:
                self.analysis_list.append(SingleAnalysis(word_str))
            except AnalysisError:
                continue
        self.compound_lemma = self.__compound_lemma()
        if self.analysis_list:
            self.pos = self.analysis_list[-1].pos

    def to_serial(self):
        analysis_list_s = (_.to_serial() for _ in self.analysis_list)
        return '{}'.format(
            '+'.join(analysis_list_s)
        )

    @staticmethod
    def from_serial(serial_str):
        return CompoundAnalysis(serial_str)

    def __eq__(self, other):
        return set(self.analysis_list) == set(other.analysis_list)

    def __hash__(self):
        hash_str = ''
        for analysis in self.analysis_list:
            hash_str += analysis.hash_str
        return hash(hash_str)

    def __str__(self):
        string = '\n{\n'
        for p in self.analysis_list:
            string += '\t' + str(p) + '\n'
        string += '}'
        return string

    def __len__(self):
        return sum(len(a.lemma) for a in self.analysis_list)

    def __flatten(self):
        for analysis in self.analysis_list:
            try:
                yield from self.__flatten(
                    frozenset(analysis.all_tags())
                )
            except TypeError:
                yield frozenset(analysis.all_tags())

    def is_compound(self):
        return len(self.analysis_list) > 1

    def contains(self, *tags):
        all_tags = frozenset.union(*self.__flatten())
        result = True
        for t in tags:
            result = result and t in all_tags
        return result

    def __compound_lemma(self):
        if self.is_compound():
            noms = []
            others = []
            for i, p in enumerate(self.analysis_list[:-1]):
                p.lemma.rstrip('-')
                if p.has_tag('Nom'):
                    noms.append((i, p.lemma))
                else:
                    others.append((i, p))
            if others:
                for i, o in others:
                    serial = o.to_serial()
                    #HACK MEH
                    if o.has_tag('Der/s') and o.lemma.endswith('nen'):
                        parts = serial.split('+')
                        parts[0] = parts[0][:-3] + 's'
                        serial = '+'.join(parts)
                    g = generate(serial)
                    noms.append((i, g))
            pieces = [
                s[1]
                for s in sorted(
                    noms,
                    key=lambda x: x[0]
                )
            ]
            pieces.append(self.analysis_list[-1].lemma.replace('-', ''))
            return '+'.join(pieces)
        else:
            return self.analysis_list[0].lemma.replace('-', '')


class WordAnalyses:
    '''
    A class containing all the possible analyses
    for a given word.
    '''
    def __init__(self, surface, parse_strs):
        self.surface = surface
        self.analyses = set()
        self.lemmas = set()
        for parse_str in parse_strs:
            cp = CompoundAnalysis(parse_str)
            # Don't add empty analyses
            if cp.analysis_list:
                self.analyses.add(cp)
                self.lemmas.add(cp.compound_lemma)
        # FIXME insanity ahead
        # splits = {}
        # lemmas = set(self.lemmas)

        # for lemma in lemmas:
        #     pieces = lemma.count('#') + 1
        #     full = lemma.replace('#', '')
        #     if pieces > 1:
        #         if full in self.lemmas:
        #             pass
        #             self.remove_with_lemma(lemma)
        #         else:
        #             # Lemma is compound
        #             if full in splits:
        #                 olemma = splits[full]
        #                 opieces = olemma.count('#') + 1
        #                 if pieces < opieces:
        #                     splits[full] = lemma
        #                     self.remove_with_lemma(olemma)
        #                 else:
        #                     self.remove_with_lemma(lemma)
        #             else:
        #                 splits[full] = lemma
    def __str__(self):
        string = 'Analyses for {}:'.format(self.surface)
        for p in self.analyses:
            string += str(p)
        string += '\nLemmas = {}'.format(self.lemmas)
        return string

    def modify_tags(self, tags):
        tag_map = language_to_tag_map.get(
            'Finnish', language_to_tag_map['DEFAULT'])
        ##- print('*** TAG MAP: %s' % tag_map)
        new_tags = dict()
        if tags != None:
            if len(tags) != 0:
                for tag in tags:
                    key = tag_map.get(tag, 'UNKNOWN')
                    if key == 'UNKNOWN':
                        if key not in new_tags:
                            new_tags[key] = []
                        new_tags[key].append(tag)
                    else:
                        new_tags[key] = tag
        return new_tags

    def to_dict(self):
        retv = []
        # retv = {}
        # retv['analyses'] = {}
        # retv['surface'] = self.surface
        # retv['analyses']['Finnish'] = []
        # retv['Finnish']['lemmas'] = self.lemmas
        for analysis in sorted(self.analyses, key=len, reverse=True):
            reading = []
            for el in analysis.analysis_list:
                dct = {}
                dct['base'] = el.lemma
                sp = analysis.analysis_list[-1]
                dct['pos'] = analyzer_to_POS_map['giella'].get(
                    sp.pos, sp.pos
                )
                dct['tags'] = self.modify_tags(el.tags)
                if hasattr(el, 'pclemma'):
                    dct['base-participle'] = el.pclemma
                reading.append(dct)
            if analysis.is_compound():
                reading[0]['canon'] = analysis.compound_lemma
            # retv['analyses']['Finnish'].append(reading)
            retv.append(reading)
        compounds = [
            p
            for p in self.analyses
            if p.is_compound()
        ]

        # if compounds: # Commented in case txema needs
        #     retv['analyses']['compounds'] = []
        #     for cp in compounds:
        #         for p in cp.analysis_list:
        #             sp_dct = {}
        #             sp_dct['base'] = p.lemma
        #             sp_dct['pos'] = p.pos
        #             sp_dct['tags'] = p.tags
        #             retv['analyses']['compounds'].append(sp_dct)
        # print(retv)
        return retv

    def to_serial(self):
        analyses_s = (_.to_serial() for _ in self.analyses)
        return '{}|{}|{}'.format(
            self.surface,
            '+'.join(self.lemmas),
            '|'.join(analyses_s)
        )

    @staticmethod
    def from_serial(serial_str):
        s = serial_str.split('|')
        if not s[1]:
            raise AnalysisError()
        wp = WordAnalyses(None, [])
        wp.surface = s[0]
        wp.lemmas = set(s[1].split('#'))
        wp.analyses = {
            CompoundAnalysis.from_serial(p)
            for l in s[2:]
            for p in l.split('|')
        }
        return wp

    def is_ambiguous(self):
        return len(self.lemmas) > 1

    def contains(self, *tags):
        result = True
        for t in tags:
            tr = False
            for p in self.analyses:
                tr = p.contains(t)
                if tr:
                    break
            result = result and tr
            if not result:
                break
        return result

    def remove_analysis(self, parse_str):
        self.analyses.discard(CompoundAnalysis(parse_str))

    def remove_if(self, *tags):
        bad = {
            p
            for p in self.analyses
            if p.contains(*tags)
        }
        for b in bad:
            # self.lemmas.discard(b.compound_lemma)
            self.analyses.discard(b)

    def remove_if_lemma_tag(self, lemma, *tags):
        bad = {
            p
            for p in self.analyses
            if p.compound_lemma == lemma
            and p.contains(*tags)
        }
        for b in bad:
            self.analyses.discard(b)
            self.lemmas.discard(b.compound_lemma)

    def remove_with_lemma(self, lemma, pos=None):
        bad = {
            p
            for p in self.analyses
            if p.compound_lemma == lemma
        }
        if pos:
            bad &= {
                p
                for p in bad
                if p.pos == pos
            }
        for b in bad:
            self.analyses.discard(b)
            self.lemmas.discard(b.compound_lemma)

    def lemmas_with(self, *tags):
        return {
            p.compound_lemma
            for p in self.analyses
            if p.contains(*tags)
        }

    def tags_for_lemma(self, lemma):
        tags = set()
        for cp in self.analyses:
            for p in cp.analysis_list:
                if sp.lemma == lemma:
                    tags.update(sp.tags)
        return tags

    def to_vector(self):
        poses = {
            cp.pos
            for cp in self.analyses
            # Sometimes we want the lemma from one analysis
            # and the POS from another.
            # tuleva -> lemma: tulla, POS: A
            # if cp.compound_lemma in self.lemmas
        }
        return [
            1 if pos in poses
            else 0
            for pos in pos_map
        ]

    def __remove_pcle(self):
        pcle = self.contains('Pcle')
        closed = False
        for tag in closed_pos:
            if self.contains(tag):
                closed = True
                break
        nn = False
        for tag in non_nominative:
            if self.lemmas_with(tag):
                nn = True
                break
        if pcle and (closed or nn):
            # self.remove_analysis(self.surface + '+Pcle')
            self.remove_if('Pcle')

    def __fix_participles(self):
        adj = self.lemmas_with('A')
        vrb = self.contains('V')
        prc_tags = (
            ('Pss', 'PrfPrc'),
            ('Act', 'PrfPrc'),
            ('Pss', 'PrsPrc'),
            ('Act', 'PrsPrc'),
            ('AgPrc',),
            ('Der/minen',)
        )
        if vrb:
            for t in prc_tags:
                prc = {
                    p.analysis_list[0]
                    for p in self.analyses
                    if p.contains(*t) and not p.is_compound()
                }
                for v in prc:
                    gen_str = '{}+V+{}+Sg+Nom'.format(
                        v.lemma,
                        '+'.join(t)
                    )
                    g = generate(gen_str)
                    if not set(v.tags) <= {'Act', 'PrsPrc', 'Pl', 'Nom'}:
                        v.pclemma = g
                    self.remove_with_lemma(g, pos='A')

    def __fix_closed(self):
        #FIXME Can this be wrong in some cases?
        bad = {
            p
            for p in self.analyses
            if self.is_ambiguous()
            and p.analysis_list[0].pos in closed_pos
            and (
                p.analysis_list[0].lemma != self.surface.lower()
                or p.analysis_list[0].tags
            )
        }
        for b in bad:
            self.analyses.discard(b)

    def __fix_infinitives(self):
        inf = self.lemmas_with('V', 'Der/minen')
        n = self.lemmas_with('N')
        if len(n) == 1 and len(inf) == 1:
            # maybe only if generate(verb) == noun
            #self.lemmas.discard(n.pop())
            self.remove_with_lemma(n.pop())

    # def __mark_capital(self):  # works if first activated
    #     """
    #     If a word capitalized:
    #     1. if in middle of sentence:
    #        return all Prop readings, do not return non-Prop readings
    #     2. if in beginning of sentence:
    #     mark all Prop readings as SUSPICIOUS
    #     3. after ANALYZER (not in this function):
    #     after all words have been analyzed:
    #     for each SUSPICIOUS lemma check:
    #        does it have other words with the same Prop lemma (capitalized) in document?
    #        if yes, then keep name
    #        if no, remove SUSPICIOUS reading
    #     """
    #     if self.surface[0].isupper():
    #         analyses = {p for p in self.analyses}
    #         for p in analyses:
    #             if self.first:
    #                 if p.contains('Prop'):
    #                     for e in p.analysis_list:
    #                         e.tags.append('SUSPICIOUS')
    #             else:
    #                 if not p.contains('Prop'):
    #                     self.remove_with_lemma(p.compound_lemma)

    def __expel_heathens(self):
        #global never_together
        heathens = set()
        for l in self.lemmas:
            if l in never_together:
                for d in never_together[l]:
                    if d in self.lemmas:
                        heathens.add(d)
        for h in heathens:
            self.remove_with_lemma(h)

    def __update_lemmas(self):
        lemmas = {
            cp.compound_lemma
            for cp in self.analyses
        }
        # FIXME not optimal?
        self.lemmas &= lemmas
        self.lemmas = {
            lemma.replace(' ', '_')
            for lemma in self.lemmas
        }

    def part_of_compound(self, lemma, key):
        for p in self.analyses:
            comp_list = p.compound_lemma.split('+')
            if key == 'compound-last':
                if lemma == comp_list[-1]:
                    return True
            if key == 'compound-first':
                if lemma == comp_list[1]:
                    return True
        return False

    def __filter_lemmas(self):
        analyses = {p for p in self.analyses}
        for p in analyses:
            for e in p.analysis_list:
                #for f in base_filter:
                if e.lemma.lower() in base_filter:#== f['base']:
                    f = base_filter[e.lemma.lower()]
                    if e.has_pos(f['pos']):
                        if 'filter' in f:
                            if 'alone' in f['filter']:
                                self.remove_if_lemma_tag(e.lemma, e.pos)
                            if 'compound' in f['filter']:
                                self.remove_with_lemma(p.compound_lemma)
                            if 'compound-last' in f['filter']:
                                key = 'compound-last'
                                if self.part_of_compound(e.lemma, key):
                                    self.remove_with_lemma(
                                        p.compound_lemma)
                        else:
                            if 'forbidden-surface' in f:
                                key = 'forbidden-surface'
                                if self.surface == f[key]:
                                    self.remove_with_lemma(e.lemma)
                            else:
                                self.remove_if_lemma_tag(e.lemma, e.pos)

    def __filter_inst(self):  # removing reading with instrumental case
        self.remove_if('Ins', 'Pl')

    def __transform_ordinals(self):
        if len(self.analyses) == 2:
            if self.contains('Num') and \
               self.contains('A'):
                self.remove_if('A')
                for p in self.analyses:
                    for e in p.analysis_list:
                        e.tags.append('Ord')

    def __fix_compounds_nonprop(self):
        compound_analyses = {
            p
            for p in self.analyses
            if p.is_compound()
        }
        for c_p in compound_analyses:
            nope = (
                #c_p.contains('Prop')
                c_p.contains('Pcle')
                or c_p.contains('Interj')
                or c_p.contains('CC')
                or c_p.contains('CS')
            )
            if nope:
                self.analyses.discard(c_p)
    def __fix_compounds_prop(self):
        compound_analyses = {
            p
            for p in self.analyses
            if p.is_compound()
            and p.contains('Prop')
        }
        diff = self.analyses - compound_analyses
        if diff:
            self.analyses = diff
    def __remove_bad_lemmas(self):  # not used
        if self.is_ambiguous():
            bad = None
            for lemma in self.lemmas:
                if lemma in bad_lemmas:
                    bad = lemma
            self.remove_with_lemma(bad)

            self.lemmas -= bad_lemmas
            # print(self.lemmas)

    def __remove_rare(self):
        self.remove_if('Use/Rare')
        self.remove_if('Use/sub')
        self.remove_if('Use/Arch')

    def __fix_digits(self):
        # removing error tags from analyses of digits like 10.5
        err_tag = 'Err/Orth'
        if re.match(r'\d+\.\d+', self.surface):
            for p in self.analyses:
                for e in p.analysis_list:
                    if (e.pos == 'Num' and
                        err_tag in e.tags):
                        e.tags.remove(err_tag)
        else:
            self.remove_if('Err/Orth')


    # FIXME dumb implementation
    def __remove_inflected(self):
        lsurf = self.surface.lower()
        if self.is_ambiguous() \
           and self.contains('N', 'Adv') \
           and self.lemmas_with('Adv').pop() == lsurf \
           and lsurf not in allowed_inflected:
            self.lemmas.discard(self.surface)

    def cleanup(self):
        # self.__remove_bad_lemmas()
        self.__filter_lemmas()
        self.__filter_inst()
        self.__transform_ordinals()
        self.__remove_pcle()
        self.__remove_rare()
        self.__fix_digits()
        self.__expel_heathens()
        self.__fix_participles()
        self.__fix_infinitives()
        self.__fix_closed()
        # self.__fix_capital()
        self.__fix_compounds_nonprop()
        self.__fix_compounds_prop()
        self.__remove_inflected()
        self.__update_lemmas()
        #self.__mark_capital()
