# -*- coding: utf-8 -*-
import os
import re
import collections
from recordtype import recordtype

from . import vocab
from . import utils
from . import tags


class VocabMap:
    def _load_vocab(self, vocab_file):
        if os.path.isfile(vocab_file):
            print(f'Reusing vocabulary {vocab_file}')
            return vocab.Vocab.load(vocab_file, self.language)
        else:
            print(f'Building vocabulary {vocab_file}')
            return vocab.Vocab(True, self.language)

    def __init__(self, surf_file, lemma_file, language, freq_dict_txt=None, freq_dict_json=None, locked=False):
        self.surf_file = surf_file
        self.lemma_file = lemma_file
        self.language = language
        self.surf_vocab = self._load_vocab(surf_file)
        self.lemma_vocab = self._load_vocab(lemma_file)
        #self.lemma_vocab.add(vocab.name_label)
        self.locked = locked
        self.pos_map_inv = pos_map_inv(self.language)
        self.freq_dict_txt = freq_dict_txt
        self.freq_dict_json = freq_dict_json

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def _get_word(self, vo, word):
        if self.locked:
            return vo[word]
        else:
            return vo.add(word)

    def _add_to_vocab_get_token(self, vo, word):
        if self.locked:
            return word
        else:
            vo.add(word)
            return word

    def _replace_surface(self, surface):
        if is_num(surface):
            return vocab.number_label
        else:
            return surface

    def _replace_lemmas(self, lemmas):
        for lemma in lemmas:
            if is_num(lemma):
                yield vocab.number_label
            elif lemma[0].isupper():
                yield vocab.name_label
            else:
                yield lemma

    def __call__(self, word, analyses=False, mode=None):
        if mode is None:
            return Word(
                    surface=self._get_word(
                    self.surf_vocab,
                    word.surface
                ),
                lemmas={
                    self._get_word(self.lemma_vocab, lemma)
                    for lemma in word.lemmas
                },
                pos={
                    map_pos(self.language, p)
                    for p in word.pos
                }
                #tags=word.tags
            )
        elif mode == 'token':
            return Simple_word(
                surface=self._add_to_vocab_get_token(
                    self.surf_vocab,
                    word.surface
                )

            )

    def print_word(self, word):
        surface = self.surf_vocab[word.surface]
        lemmas = {
            self.lemma_vocab[lemma]
            for lemma in word.lemmas
        }
        poses = {
            self.pos_map_inv[pos]
            for pos in word.pos
        }
        print(f'(s={surface}, l={lemmas}, p={poses})')

    def save(self):
        self.surf_vocab.save(self.surf_file)
        if self.freq_dict_json is not None and self.freq_dict_txt is not None:
            self.surf_vocab.save_freq_dict(self.freq_dict_txt, self.freq_dict_json)
        self.lemma_vocab.save(self.lemma_file)


def map_pos(language, pos):
    mp = tags.pos_map[language]
    if pos in mp:
        return mp[pos]
    else:
        return mp['Other']


#Word = recordtype('Word', ['surface', 'lemmas', 'pos', 'tags'])
Word = recordtype('Word', ['surface', 'lemmas', 'pos'])
Simple_word = recordtype('Word', ['surface'])
##maybe negative form should be created here, with info about neg forms tag
##if we need to get tags for all negative forms -- we will need to call for an analyser for them

PAD = Word(
    surface=vocab.padding_label,
    lemmas={vocab.padding_label},
    pos={'Other'}
    #tags={-1}
)
NUM = Word(
    surface=vocab.number_label,
    lemmas={vocab.number_label},
    pos={'Num'}
    #tags={-1}
)
UNK = Word(
    surface=vocab.unknown_label,
    lemmas={vocab.unknown_label},
    pos={'Other'}
    #tags={-1}
)

PUNCT = Word(
    surface=vocab.punct_label,
    lemmas={vocab.punct_label},
    pos={'Other'}
)

LAT = Word(
    surface=vocab.lat_label,
    lemmas={vocab.lat_label},
    pos={'Other'}
)

NAME = Word(
    surface=vocab.name_label,
    lemmas={vocab.name_label},
    pos={'Other'}
)

SPAD = Simple_word(
    surface=vocab.padding_label
)
SNUM = Simple_word(
    surface=vocab.number_label
)
SUNK = Simple_word(
    surface=vocab.unknown_label)

SNAME = Simple_word(
    surface=vocab.name_label
)

SLAT = Simple_word(
    surface=vocab.lat_label
)


num_pat = re.compile(r'\d[-\d\.]*')

@utils.memoize
def is_num(surface):
    return num_pat.fullmatch(surface)

def pos_count(language):
    pm = tags.pos_map[language]
    return len(set(pm.values()))

def tags_count(language):
    tm = tags.tag_map[language]
    return len(set(tm.values()))

def pos_map_inv(language):
    pm = tags.pos_map[language]
    return dict((v, k) for k, v in pm.items())

def split_compound(surface, analyses):
    is_compound = any(len(a) > 1 for a in analyses)
    if is_compound:
        analysis = analyses[0]
        if 'canon' in analysis[0]:
            canon = analysis[0]['canon']
            surfaces = canon.split('+')
            ilast = sum(len(s) for s in surfaces[:-1])
            surfaces[-1] = surface[ilast:]
            lemmas = (
                piece['base']
                for piece in analysis
            )
            poses = (
                piece['pos']
                for piece in analysis
            )
            return [
                Word(
                    surface=surf,
                    lemmas={lemma},
                    pos={pos}
                )
                for surf, lemma, pos in zip(surfaces, lemmas, poses)
            ]
        else:
            # The compound exists as a single lemma in the lexicon,
            # take just that reading and assume it is correct.
            return [
                Word(
                    surface=surface,
                    lemmas={analysis[0]['base']},
                    pos={analysis[0]['pos']}
                )
            ]
    else:
        poses = set()
        lemmas = set()
        for analysis in analyses:
            lemmas.add(analysis[0]['base'])
            poses.add(analysis[0]['pos'])
            
        return [
            Word(
                surface=surface,
                lemmas=lemmas,
                pos=poses,
            )
        ]


def get_word_object(surface, analyses):
    poses = set() #we never use these two sets together so they do not match
    lemmas = set()
    #tags = get_tags(analyses, language)
    for analysis in analyses:
        lemmas.add(analysis[0]['base'])
        poses.add(analysis[0]['pos'])
    return Word(
            surface=surface,
            lemmas=lemmas,
            pos=poses)
            #tags=tags)

def get_word_object_simplified(surface):
    return Simple_word(
            surface=surface
        )

def get_tags(analyses, language):
    tag_dict = dict()
    tm = tags.tag_map[language]
    for analysis in analyses:
        tgs = analysis[0]['tags']
        for k, v in tgs.items():
            if k not in tag_dict:
                tag_dict[k] = set()
                tag_dict[k].add(v)
            else:
                tag_dict[k].add(v)
    tag_dict = modify_tags(tag_dict, language)
    result = {tm[t] for t in tag_dict if t in tm}
    if not result:
        result.add(-1)
    return result
    
def modify_tags(tag_dict, language):
    tags = set()
    if language == 'Russian':
        if 'NUMBER' in tag_dict and 'CASE' in tag_dict:
            for nc in tag_dict['NUMBER']:
                for cc in tag_dict['CASE']:
                    tags.add(nc+cc)
        if 'NUMBER' in tag_dict and 'PERSON' in tag_dict:
            for nt in tag_dict['NUMBER']:
                for pc in tag_dict['PERSON']:
                    tags.add(nt+pc)
        for c, v in tag_dict.items():
            if c not in ['NUMBER', 'CASE', 'PERSON']:
                for el in v:
                    tags.add(el)
    return tags
        
    

