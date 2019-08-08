# -*- coding: utf-8 -*-

import os
import ujson
import hashlib
import codecs
from collections import defaultdict

from tokenizer import Tokenizer
from analyser.analyzer_wrapper import Analyzer

from utils import dataset
import random
import string

CACHE_DIR = '.cache'
if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR)


# Russian
def map_characters(token):
    ch_map = {
        'e': 'е',
        'y': 'у',
        'o': 'о',
        'p': 'р',
        'a': 'а',
        'c': 'с',
        'E': 'Е',
        'O': 'О',
        'P': 'Р',
        'A': 'А',
        'C': 'С',
        'B': 'В',
        'K': 'К',
        'M': 'М',
        'T': 'Т',
        'H': 'Н',
        'x': 'х',
        'X': 'Х'
    }
    if token is not None:
        for k in list(ch_map.keys()):
            token = token.replace(k, ch_map[k])
    return token


def fix_e(word):
    new_word = word.replace('ё', 'е')
    return new_word


def modify_hyphened(word):
    endings = ['ка', 'с', 'а']
    if any([word.endswith(e) for e in endings]):
        word = word.split('-')[0]
    elif word.startswith('-') or word.endswith('-'):
        word = word.strip('-')
    #TODO: Should we remove the second part of words with hyphen? or leave it
    else:
       word = word.split('-')[-1]
    return word


class BadTagsComb:
    def __init__(self, lang):
        self.lang = lang
        self.tags = {}
        self.cache_file = self._cache_fname()
        self.load()

    def _cache_fname(self):
        return os.path.join(CACHE_DIR, f'tags_comb_{self.lang}.json')

    def load(self):
        if os.path.isfile(self.cache_file):
            print('Loading tags combinations from cache')
            with open(self.cache_file, 'r') as cf:
                self.tags.update(ujson.load(cf))

    def update_tags(self, pos, comb):
        if pos not in self.tags:
            self.tags[pos] = []
            # print("New pos", pos)
        if comb not in self.tags[pos]:
            self.tags[pos].append(comb)

    def check_tags(self, pos, comb):
        if pos in self.tags and comb in self.tags[pos]:
            # print(f"Found bad comb {comb} in {pos}")
            return True
        return False

    def save(self):
        with open(self.cache_file, 'w') as cf:
            ujson.dump(self.tags, cf, ensure_ascii=False)


class MemoAnalyser:
    def _cache_fname(self):
        return os.path.join(CACHE_DIR, f'analyses_{self.lang}.json')

    def analyse(self, arg):
        if arg not in self.results:
            a = self.analyser.analyze(arg)
            self.results[arg] = a['analyses'][self.lang]
        return self.results[arg]

    def load(self):
        if os.path.isfile(self.cache_file):
            print('Loading analyses from cache')
            with open(self.cache_file, 'r') as cf:
                self.results.update(ujson.load(cf))

    def save(self):
        with open(self.cache_file, 'w') as cf:
            ujson.dump(self.results, cf, ensure_ascii=False)

    def __init__(self, lang):
        self.lang = lang
        self.analyser = Analyzer(lang)
        self.results = {}
        self.cache_file = self._cache_fname()
        self.load()

    def __next__(self):
        return next(self.generator)


class BatchTokenizer:
    def _cache_fname(self, fname):
        h = hashlib.sha1(os.path.abspath(fname).encode()).hexdigest()
        return os.path.join(CACHE_DIR, f'{h}_{self.lang}.json')

    def _cached_gen(self, docs_cache):
        with open(docs_cache, 'r') as dc:
            for doc in dc:
                yield ujson.loads(doc)

    def _make_gen(self, fname, docs_cache):
        with codecs.open(fname, 'r', encoding='utf-8', errors='ignore') as inf, \
                open(docs_cache, 'w') as dc:
            for doc in filter(bool, inf):
                sents = self.tokenizer.tokenize(doc)
                print(ujson.dumps(sents, ensure_ascii=False), file=dc)
                yield sents

    def __init__(self, lang, fname):
        self.lang = lang
        docs_cache = self._cache_fname(fname)
        if os.path.isfile(docs_cache):
            print('Loading tokenized documents from cache')
            self.generator = self._cached_gen(docs_cache)
        else:
            self.tokenizer = Tokenizer(lang)
            self.generator = self._make_gen(fname, docs_cache)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.generator)


class DocMapper:
    def _fi_make_gen(self, doc):
        for i, sent in enumerate(doc):
            if not self.analyser:
                sent = sent['features']
            for j, word in enumerate(sent):
                self._curr = (i, j)
                if self.analyser:
                    surface = surface.lower()
                    analyses = self.analyser.analyse(surface)
                else:
                    surface = word['surface'].lower()
                    analyses = word['analyses']
                if surface in self.names:
                    yield self.vomap(dataset.NAME)
                elif surface in ['PAD', 'pad']:
                    yield self.vomap(dataset.PAD)
                elif surface in string.punctuation or surface in ['``', '„'] or word['pos'] == 'PUNCT':
                    yield self.vomap(dataset.PUNCT)
                elif dataset.is_num(surface) or surface in ['NUM', 'num']:
                    yield self.vomap(dataset.NUM)
                elif self.freq_dict and surface not in self.freq_dict:
                    yield self.vomap(dataset.UNK)
                elif self.freq_dict and surface in self.freq_dict and self.freq_dict[surface] == 1:
                    yield self.vomap(dataset.UNK)
                elif analyses:
                    yield self._process_word(surface, analyses)


    def _ru_make_simple_gen(self, doc):
        for i, sent in enumerate(doc):
            for j, word in enumerate(sent):
                self._curr = (i, j)
                word = map_characters(word)
                yield word

    def _ru_make_gen(self, doc):
        for i, sent in enumerate(doc):
            for j, word in enumerate(sent):
                self._curr = (i, j)
                word = word.lower()
                word = map_characters(word)
                e_word = fix_e(word)  # Ugly hack
                analyses = self.analyser.analyse(e_word)
                if word in self.names:
                    yield self.vomap(dataset.NAME)
                elif word in ['PAD', 'pad']:
                    yield self.vomap(dataset.PAD)
                elif word in string.punctuation or word in ['``', '„']:
                    yield self.vomap(dataset.PUNCT)
                elif dataset.is_num(word) or word in ['NUM', 'num']:
                    yield self.vomap(dataset.NUM)
                elif word in ['LAT', 'lat']:
                    yield self.vomap(dataset.LAT)
                elif self.freq_dict and word not in self.freq_dict:
                    yield self.vomap(dataset.UNK)
                elif self.freq_dict and word in self.freq_dict and self.freq_dict[word] == 1:
                    yield self.vomap(dataset.UNK)
                elif analyses:
                    yield self._process_word(word, analyses)
                else:
                    if '-' in word and len(word) > 2:
                        word = modify_hyphened(word)
                        e_word = fix_e(word)
                        analyses = self.analyser.analyse(e_word)
                        if analyses:
                            yield self._process_word(word, analyses)
                        else:
                            yield self.vomap(dataset.UNK)
                    else:
                        yield self.vomap(dataset.UNK)


    def _process_word(self, word, analyses):
        if self.language == 'Russian':
            token = dataset.get_word_object(word, analyses)
        elif self.language == 'Finnish':
            token = dataset.split_compound(word, analyses)
        tokens = []
        if type(token) == list:
            for t in token:
                tokens.append(self.vomap(t))
        if tokens:
            return tokens
        else:
            return self.vomap(token)


    def __init__(self, doc, analyser, vomap, language, names, freq_dict=None, mode=None):
        self._curr = (0, 0)
        self._count = 0
        self.index = defaultdict(list)
        self.language = language
        self.tag_vect = True
        self.analyser = analyser
        self.vomap = vomap
        self.freq_dict = freq_dict
        self.mode = mode
        self.names = names
        if self.language == 'Russian':
            if self.mode == 'token':
                self.generator = self.ru_make_simple_gen(doc)
            else:
                self.generator = self._ru_make_gen(doc)
        elif self.language == 'Finnish':
            self.generator = self._fi_make_gen(doc)

    def __iter__(self):
        return self

    def __next__(self):
        ret = next(self.generator)
        self.index[self._curr].append(self._count)
        self._count += 1
        return ret
