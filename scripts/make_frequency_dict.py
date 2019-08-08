#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sys, os, re, pickle, argparse, string
import numpy as np
import subprocess as sp
import multiprocessing as mp
from multiprocessing.managers import BaseManager, NamespaceProxy
from collections import OrderedDict
from disambiguation import *



def filter_word(word):
    if re.match(r'\d+', word):
        return None
    if not re.match(r'\w+', word):
        return None
    if len(word) > 1:
        w = word.lstrip(string.punctuation)
        w = w.rstrip(string.punctuation)
        return w.lower()
    else:
        return word.lower()
    
'''
Split an input text into tokens using OpenNLP
and tidy up the result a bit.
'''
def tokenize_task(input_file):

    dictionary = {}
    
    print("*****input file")
    print(input_file)
    with open(input_file, 'r') as f:
        onlp = os.path.join(resources, 'apache-opennlp-1.8.2/bin/opennlp')
        smodel = os.path.join(resources, 'token-models/fi-sent.bin')
        tmodel = os.path.join(resources, 'token-models/fi-token.bin')
        sproc = sp.run(
            [onlp, 'SentenceDetector', smodel],
            stdout = sp.PIPE,
            stderr = sp.DEVNULL,
            stdin = f
        )
        tproc = sp.run(
            [onlp, 'TokenizerME', tmodel],
            stdout = sp.PIPE,
            stderr = sp.DEVNULL,
            input = sproc.stdout
        )
        text = str(tproc.stdout, 'utf-8')
        pattern = r'(--|»|\||\#)'
        text = re.sub(re.compile(pattern), '', text)
        pattern = r'\n+'
        text = re.sub(re.compile(pattern), '\n', text)
        sents = text.split('\n')
        words = []
        for s in filter(bool, sents):
            # words.append(list(filter(bool, s.split(' '))))
            for w in filter(bool, s.split(' ')):
                word = filter_word(w)
                if word:
                    dictionary[word] = dictionary.get(word, 0) + 1
                else:
                    continue

        progress_multip(count, total)
    return dictionary


def initializer():
    global dictionary
    dictionary = dict()

def make_freq_dict(file_list):
    global count
    count = mp.Value('I', 0)
    pool = mp.Pool(processes = os.cpu_count())
    tokens = pool.map(tokenize_task, file_list)
    pool.close()
    pool.join()
    freq_dict = dict()
    print('Creating a word frequency dict')
    for t in tokens:
        print(t)
        for s in t:
            for w in s:
                word = filter_word(w)
                if word:
                    freq_dict[word] = freq_dict.get(word, 0) + 1
                else:
                    continue
    d = OrderedDict(sorted(freq_dict.items(), key=lambda t: int(t[1]), reverse=True))
    del tokens                
    return d



def make_freq_dict(dict_list):
    global count
    count = mp.Value('I', 0)
    pool = mp.Pool(processes = os.cpu_count())
    dictionaries = pool.map(tokenize_task, file_list)
    pool.close()
    pool.join()
    freq_dict = dict()
    print('Creating a word frequency dict')
    for d in dictionaries:
        #print(t)
        for word, count in d.items():
            word = filter_word(word)
            if word:
                freq_dict[word] = freq_dict.get(word, 0) + count
            else:
                continue
    d = OrderedDict(sorted(freq_dict.items(), key=lambda t: int(t[1]), reverse=True))
    return d





if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', metavar = 'PATH', type=str, help = 'Path to the source text')
    args = parser.parse_args()
    print(args.path)

    total = len(os.listdir(args.path))
    texts = os.scandir(args.path)
    file_list = (t.path for t in texts)

    freq_dict = make_freq_dict(file_list)
    # print(freq_dict)
    print('Frequency dict is created, {} items'.format(len(freq_dict)))
    print('Loading data')
    with open('frequency_table.pck', 'wb') as f:
        pickle.dump(freq_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
        

    
