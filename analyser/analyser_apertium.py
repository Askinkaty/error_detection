#!/cs/puls/pyenv/shims/python
# -*- coding: utf-8 -*-

import re
import subprocess as sp
from pprint import pprint

from . import analyzers_config as ac
from .analyzer_base import BaseAnalyzer

class ApertiumAnalyser(BaseAnalyzer):
    def __init__(self, lang, analyser_file):
        super().__init__(lang, analyser_file)

    def __map_pos(self, pos):
        try:
            return ac.analyzer_to_POS_map['apertium'][pos]
        except KeyError:
            return 'Other'

    def __map_tag(self, tag):
        try:
            return ac.language_to_tag_map['apertium'][tag]
        except KeyError:
            return 'UNKNOWN'

    def __parse(self, an_out):
        readings = (_[0] for _ in an_out)
        an_dict = {
            'analyses': {self.language: []},
        }
        an_hashes = set()
        for rs in readings:
            pieces = []
            phash = ''
            for r in rs.split('+'):
                sep = r.index('<')
                lemma = self.__delete_superscript(r[:sep])
                tags = re.findall('<[^>]*>', r[sep:])
                pos = tags[0][1:-1]
                mpos = self.__map_pos(pos)
                piece = {
                    'base': lemma,
                    'pos': mpos,
                    'tags': {}
                }
                phash += '{}{}'.format(
                    mpos,
                    "".join(sorted(tags[1:]))
                )
                for tag in tags[1:]:
                    tag = tag[1:-1]
                    mtag = self.__map_tag(tag)
                    if mtag == 'UNKNOWN':
                        if mtag not in piece['tags']:
                            piece['tags'][mtag] = []
                        piece['tags'][mtag].append(tag)
                    else:
                        piece['tags'][mtag] = tag
                pieces.append(piece)
            if phash not in an_hashes:
                an_dict['analyses'][self.language].append(pieces)
            an_hashes.add(phash)
        return an_dict

    def __delete_superscript(self, word):
        word = re.sub(r'[¹²]', '', word)
        return word


    def analyze(self, word, first=False):
        an_out = self.analyzer.lookup(word, output='tuple')
        if word[0].isupper():
            an_outl = self.analyzer.lookup(word.lower(), output='tuple')
            an_out += an_outl
        an_dict = self.__parse(an_out)
        an_dict['surface'] = word
        return an_dict
