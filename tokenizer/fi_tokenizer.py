# -*- coding: utf-8 -*-

import os
import re
import string
import ujson

from . import BaseTokenizer

from py4j.java_gateway import JavaGateway

ONLP_TOOLS = '/Resources/apache-opennlp-1.8.2/...'
SENT_FILE = 'Resources/token-models/fi-sent.bin'
TOKEN_FILE = 'Resources/token-models/fi-token.bin'

class FinnishTokenizer(BaseTokenizer):
    lang = 'Finnish'

    def __init__(self):
        gateway = JavaGateway.launch_gateway(
            classpath=ONLP_TOOLS,
            die_on_exit=True
        )
        spkg = gateway.jvm.opennlp.tools.sentdetect
        tpkg = gateway.jvm.opennlp.tools.tokenize
        fis = gateway.jvm.java.io.FileInputStream
        sfile = fis(SENT_FILE)
        smodel = spkg.SentenceModel(sfile)
        self.sdet = spkg.SentenceDetectorME(smodel)
        tfile = fis(TOKEN_FILE)
        tmodel = tpkg.TokenizerModel(tfile)
        self.tok = tpkg.TokenizerME(tmodel)

        pattern = r'(--|»|\||\#)'
        self.bad_chars = re.compile(pattern)
        pattern = r'\n+'
        self.newlines = re.compile(pattern)

    def _clean_word(self, word):
        '''
        Remove punctuation at the beginning and end of the
        word, unless it's a single punctuation sign.
        '''
        if len(word) > 1:
            w = word.lstrip(string.punctuation)
            w = w.rstrip(string.punctuation)
            if w.isupper():
                return w.lower()
            else:
                return w
        else:
            return word

    def tokenize(self, doc):
        text = re.sub(self.bad_chars, '', doc)
        text = re.sub(self.newlines, '\n', text)
        return [
            [
                self._clean_word(token)
                for token in self.tok.tokenize(sent)
            ]
            for sent in self.sdet.sentDetect(text)
        ]
