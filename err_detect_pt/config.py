# -*- coding: utf-8 -*-

import os

DEFAULT_LANG = 'Russian'
# DEFAULT_LANG = 'Finnish'
# DEFAULT_LANG = 'Sakha'


LANG = os.getenv('DA_LANG', DEFAULT_LANG)

print(LANG)

WINDOW_RAD = 10

RUN_BASE = '/cs/experiments/err_detect'
TMP_BASE = '/scratch/err_detect_out'
CORPUS_BASE = '/cs/puls/' #replace by other dir with corpus data
VECTORS_BASE = '/cs/puls/Resources/embeddings/fText/'

LANG_MAP = {
    'Finnish': {
        'vectors': 'cc.fi.300.bin',
        'corpus': '/Corpus/ftc_parsed_all.txt'
    },
    'Russian': {
        'vectors': 'cc.ru.300.bin',
        'corpus': '/Projects/word2vec/russian/word2vec/russian/ru_norm.txt'
    },
    'Sakha': {
        'vectors': 'cc.sah.300.bin',
        'corpus': '/Corpus/Sakha/sakha.txt'
    }
}

class Config:
    def __init__(self, lang=LANG):
        self.lang = lang
        self.window_rad = WINDOW_RAD
        self.model_args = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'model',
            'args_def.json'
        )
        self._load_attrs()

    def _load_attrs(self):
        self.run_dir = os.path.join(RUN_BASE, self.lang)
        self.tmp_dir = os.path.join(TMP_BASE, self.lang)
        self.cache_dir = os.path.join(self.tmp_dir, 'cache')
        self.lemma_file = os.path.join(self.tmp_dir, 'lemmas.txt')
        self.surface_file = os.path.join(self.tmp_dir, 'surfaces.txt')
        self.vector_file = os.path.join(
            self.tmp_dir,
            LANG_MAP[self.lang]['vectors']
        )
        self.corpus_file = os.path.join(
            CORPUS_BASE,
            LANG_MAP[self.lang]['corpus']
        )

    def reset(self, lang):
        self.lang = lang
        self._load_attrs()

    def __str__(self):
        return str(self.__dict__)
