# -*- coding: utf-8 -*-

import re
from multiprocessing.managers import BaseManager, NamespaceProxy
import json
#new
padding_label = 'pad'
unknown_label = 'unk'
number_label = 'num'
name_label = 'name'
punct_label = 'punct'
lat_label = 'lat'
#old
# padding_label = 'PAD'
# unknown_label = 'UNK'
# number_label = 'NUM'
# name_label = 'NAME'
# punct_label = 'PUNCT'
# lat_label = 'LAT'


class Vocab():
    def __init__(self, special_labels=False, language=None):
        self.word2index = {}
        self.index2word = {}
        self.word_freq = {}
        self.index = 0
        self.language = language
        if special_labels:
            self.add(padding_label)
            self.add(unknown_label)
            self.add(number_label)
            self.add(punct_label)
            #not in old
            self.add(name_label)
            self.add(lat_label)

    def add(self, word):
        #TODO: words are lowercased to check if they are already in the vocab
        #but do I lowercase (check if they are in the vocab) them when reading data? Should I?
        if word not in self.word2index:
            self.word2index[word] = self.index
            self.index2word[self.index] = word
            self.index += 1
            self.word_freq[word] = 1
            return self.index - 1
        
        else:
            self.word_freq[word] += 1
            return self.word2index[word]
    
    def check_word(self, word):
        if word in self.word2index:
            return True
        else:
            return False
        
    def save(self, output_file):
        with open(output_file, 'w') as f:
            for i in range(self.index):
                try:
                    print(self.index2word[i], file=f)
                # Just in case there's a missing key
                except KeyError:
                    continue
                
    def save_freq_dict(self, output_file, output_file_json):
        sorted_dict = sorted(self.word_freq.items(), key=lambda kv: kv[1], reverse=True)
        n = 0
        for value in self.word_freq.values():
            if value > 1:
                n += 1
        print('Length of dict without words with freq=1:', n)
        with open(output_file_json, 'w', encoding='utf-8') as f:
            json.dump(self.word_freq, f, ensure_ascii=False)
        with open(output_file, 'w') as f1:
            for k, v in sorted_dict:
                try:
                    print(k + ': ' + str(v), file=f1)
                except KeyError:
                    continue
            
    @staticmethod
    def load(input_file, language):
        vocab = Vocab(True, language)
        with open(input_file, 'r') as f:
            for word in f:
                vocab.add(word.strip())
        print(vocab.index)
        return vocab

    def __getitem__(self, key):
        t = type(key)
        try:
            if t == str:
                return self.word2index[key]
            elif t == int:
                return self.index2word[key]
            else:
                raise KeyError(key)
        except KeyError:
            return self.word2index[unknown_label]

    def __len__(self):
        return self.index

    def __iter__(self):
        return iter(self.word2index.keys())

    def __str__(self):
        return '\n'.join(
            f'{i} -> {self.index2word[i]}'
            for i in range(self.index)
        )


class VocabManager(BaseManager):
    pass


class VocabProxy(NamespaceProxy):
    _exposed_ = (
        '__getattribute__',
        '__setattr__',
        '__delattr__',
        '__getitem__',
        '__len__',
        'add',
        'save'
    )

    def add(self, word):
        return self._callmethod('add', [word])

    def save(self, output_file):
        return self._callmethod('save', [output_file])


VocabManager.register('Vocab', Vocab, VocabProxy)
