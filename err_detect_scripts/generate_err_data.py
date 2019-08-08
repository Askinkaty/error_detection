#!/cs/puls/pyenv/shims/python
# -*- coding: utf-8 -*-

import os
import sys
import ujson
import json
from typing import List, Any


from datetime import datetime
from analyser.analyzer_wrapper import Analyzer
import numpy as np
import tensorflow as tf
from tqdm import tqdm

import random
from os.path import dirname

sys.path.append(dirname(sys.path[0]))
# from tokenizer import Tokenizer
import codecs
from pymongo import MongoClient

from utils import utils
from utils import dataset
from utils import vocab
from utils import pipeline
import time
import csv

from polyglot.text import Text

LANG = 'Russian'
LANG = 'Finnish'

window_rad = 10
max_lemmas = 5
stride = 3


def hs_mongo():
    mongodb_uri = "..."
    mongodb_name = "..."
    connection = MongoClient(mongodb_uri, socketTimeoutMS=3_600_000)
    db = connection[mongodb_name]
    db.articles = db['articles']
    db.articles_test = db['articles_test']
    return db


def load_vocab(vocab_file):
    new = not os.path.isfile(vocab_file)
    if new:
        print(f'Building vocabulary {vocab_file}')
        vo = vocab.Vocab(True, LANG)
    else:
        print(f'Reusing vocabulary {vocab_file}')
        vo = vocab.Vocab.load(vocab_file, LANG)
    return vo, new


def make_windows(adoc, stride):
    return utils.SlidingWindow(
        adoc,
        window_rad,
        stride,
        pad=vomap(dataset.PAD)
    )


def make_windows_simple(adoc, stride):
    return utils.SlidingWindow(
        adoc,
        window_rad,
        stride,
        pad='PAD'
    )


def window_to_example(window, label, format):
    if format == 'tfrecord':
        return window_to_example_form(window, label)
    elif format == 'csv':
        return window_to_example_csv(window, label)


def window_to_example_csv(window, label, token=None):
    sent = [label]
    pad_unk = 0
    for i, word in enumerate(window):
        if word.surface in [0, 1]:
            pad_unk += 1
        if token:
            if word == ',':
                word = '#'
            s = vomap.surf_vocab[word.surface]
            sent.append(s)
        else:
            sent.append(word.surface)
    if pad_unk > 0.5 * (window_rad * 2 + 1):
        return None
    else:
        return sent


def window_to_example_form(window, label):
    pad_unk = 0
    sent = np.empty(len(window), dtype=int)
    for i, word in enumerate(window):
        if word.surface in range(6):  # pad, unk, num, punct, name, lat
            pad_unk += 1
        sent[i] = word.surface
    feature = {
        'sent': tf.train.Feature(
            int64_list=tf.train.Int64List(
                value=sent
            )
        ), 'label': tf.train.Feature(
            int64_list=tf.train.Int64List(
                value=[label]
            )
        )}
    example = tf.train.Example(
        features=tf.train.Features(
            feature=feature
        )
    )
    if pad_unk > 0.5 * (window_rad * 2 + 1):  # remove phrase with too many pads, unk, names, lat, punct
        return None
    else:
        return example.SerializeToString()



def is_train():
    split = 0.1
    if random.uniform(0, 1) > split:
        return True
    else:
        return False


def get_forms(surface, n_forms):
    all_forms = []
    if surface in inflections:
        infl_forms = inflections[surface]
        all_forms.extend(infl_forms)
    if len(all_forms) > n_forms:
        return random.sample(all_forms, n_forms)
    else:
        return all_forms


def write(example, format, negative=None, positive=None):
    if format == 'tfrecord':
        if is_train():
            writer_train.write(example)
        else:
            writer_valid.write(example)
    elif format == 'csv' or format == 'csv_token':
        if negative:
            if is_train():
                writer_negative.writerow(example)
        elif positive:
            if is_train():
                writer_positive.writerow(example)
        else:
            if is_train():
                writer_train.writerow(example)
            else:
                writer_valid.writerow(example)


def modify_neg_window(window, median, surface):
    nindex = vomap.surf_vocab.add(surface)
    median.surface = nindex
    window[window_rad] = median
    new_window = [vomap(dataset.PAD)] + window[:window_rad - 1] + window[window_rad:]
    return new_window


def build_train_form_predict(in_file, freq_dict, format):
    t_overall_started = time.time()
    total = utils.count_lines(in_file)
    docs = pipeline.BatchTokenizer(LANG, in_file)
    pos = 0
    neg = 0

    for doc in tqdm(docs, total=total):
        if not doc:
            continue
        words = []
        for s in doc:
            words.extend(s)
        snippet = ' '.join(words)
        text = Text(snippet, hint_language_code='ru')
        names = []
        for e in text.entities:
            if e.tag == 'I-PER':
                names.extend(e)
        names = [e.lower() for e in names if e not in ['NAME', 'LAT', 'PAD', 'NUM', 'UNK', 'name', 'lat', 'pad', 'num',
                                                       'unk']]
        dm = pipeline.DocMapper(doc, analyser,
                                vomap,
                                LANG, names,
                                freq_dict)
        windows = make_windows(list(dm), stride)
        for window in windows:
            assert len(window) == (window_rad * 2) + 1
            median = window[window_rad]
            # if the word is unambiguous
            if len(median.lemmas) == 1:
                # positive example.;
                p_example = window_to_example(window, 1, format)
                if random.uniform(0, 1) > 0.60 and p_example:  # save only half of all positive forms
                    pos += 1
                    write(p_example, format, positive=True)
                surface = vomap.surf_vocab[median.surface].lower()
                neg_num = 1
                negative_forms = get_forms(surface, neg_num)

                if negative_forms:
                    for f in negative_forms:
                        if f.replace('ё', 'е') != surface:
                            findex = vomap.surf_vocab.add(f)
                            replacement = dataset.Word(surface=findex,
                                                       lemmas=median.lemmas,
                                                       pos=median.pos)
                            window[window_rad] = replacement
                            # create negative example
                            n_example = window_to_example(window, 0, format)
                            if n_example:
                                neg += 1
                                write(n_example, format, negative=True)
                # print("Done with negative forms")
            else:
                # create positive window
                p_example = window_to_example(window, 1, format)
                if random.uniform(0, 1) > 0.60 and p_example:
                    write(p_example, format, positive=True)
                    pos += 1
    print(f'Positive ex: {pos}, Negative ex: {neg}')
    print(f'Overall time: {time.time() - t_overall_started}')


if __name__ == '__main__':
    language = 'Russian'
    analyser = Analyzer(language)
    surf_vocab = 'experiments/ErrData/ru/new_data/surfaces.txt'
    lemma_vocab = 'experiments/ErrData/ru/new_data/lemmas.txt'
    freq_dict_json = '/experiments/ErrData/ru/new_data/freq_dict.json'

    inflections_file = '../../new_final_inflections.json'
    vomap = dataset.VocabMap(surf_vocab, lemma_vocab, LANG)
    neg_examples = True
    with_db = False
    format = 'tfrecord'
    # format = 'csv'
    # format = None

    with codecs.open(inflections_file, 'r', encoding='utf-8') as f:
       inflections = json.load(f)

    # Use freq dict to exclude rare words
    with codecs.open(freq_dict_json, 'r', encoding='utf-8') as fd:
        freq_dict = json.load(fd)
    in_file = 'Projects/russian/text.txt'

    if format == 'csv':
        with codecs.open('/experiments/ErrData/ru/csv_kp_data/negative.csv', mode='w') as negative_csv_file, \
                codecs.open('/experiments/ErrData/ru/csv_kp_data/positive.csv', mode='w') as positive_csv_file:
            writer_negative = csv.writer(negative_csv_file, delimiter='|', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer_positive = csv.writer(positive_csv_file, delimiter='|', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            print('Building training instances')
            format = 'csv_token'
            build_train_form_predict(in_file, freq_dict, format)
            print('Writing files...')

    elif format == 'tfrecord':
        out_train_file = '/experiments/ErrData/ru/small_data/train.tfrecord'
        out_valid_file = '/experiments/ErrData/ru/small_data/valid.tfrecord'
        out_additional_test_file = '/experiments/ErrData/ru/new_data/random_pos.tfrecord'
        writer_train = tf.python_io.TFRecordWriter(out_train_file)
        writer_valid = tf.python_io.TFRecordWriter(out_valid_file)
        writer_train = tf.python_io.TFRecordWriter(out_additional_test_file)

        print('Building training instances')
        build_train_form_predict(in_file, freq_dict, format)
        print('Writing files...')
    vomap.save()
