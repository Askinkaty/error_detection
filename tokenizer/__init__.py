# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod

__all__ = ['fi_tokenizer']

class BaseTokenizer(metaclass=ABCMeta):
    @abstractmethod
    def tokenize(self, doc):
        pass

from . import *

LANG_MAP = {
    cls.lang: cls
    for cls in BaseTokenizer.__subclasses__()
}

from nltk.tokenize import sent_tokenize, word_tokenize

class GenericTokenizer(BaseTokenizer):
    def tokenize(self, doc):
        return [
            word_tokenize(sent)
            for sent in sent_tokenize(doc)
        ]

class Tokenizer:
    def __init__(self, lang):
        self.backend = LANG_MAP.get(lang, GenericTokenizer)()
        self.tokenize = self.backend.tokenize
