# -*- coding: utf-8 -*-

import os
import pickle
import argparse
import ujson
import pymongo
import curses

import subprocess as sp

from functools import partial
from string import Formatter


class SlidingWindow:
    def __init__(self, document, window_size, stride, pad=None):
        self.doc = document
        self.dlen = len(document)
        self.winsize = window_size
        self.stride = stride
        self.count = 0
        self.pad = pad

    def get_window(self, index):
        if index > self.dlen:
            return [self.pad] * (self.winsize * 2 + 1)
        start = index - self.winsize
        spad = abs(min(start, 0))
        start = max(start, 0)
        end = index + 1 + self.winsize
        epad = abs(min(self.dlen - end, 0))
        end = min(end, self.dlen)
        return (
            [self.pad] * spad
            + self.doc[start:end]
            + [self.pad] * epad
        )

    def __iter__(self):
        return self

    def __next__(self):
        if self.count >= self.dlen:
            raise StopIteration
        else:
            window = self.get_window(self.count)
            self.count += self.stride
            return window


class BulkWriter:
    def __init__(self, collection, max_ops=1000):
        self.collection = collection
        self.op_count = 0
        self.max_ops = max_ops
        self.ops = []

    def execute(self):
        self.collection.bulk_write(self.ops)
        self.ops = []

    def insert(self, dictionary):
        self.ops.append(pymongo.InsertOne(dictionary))
        if len(self.ops) >= self.max_ops:
            self.execute()


class MongoDict:
    def __init__(self, collection, key):
        self.dictionary = {}
        self.collection = collection
        self.key = key
        self.modified = False
        self.not_found = set()

    def __cache(self, value):
        if value in self.not_found:
            return False
        else:
            record = self.collection.find_one({self.key: value})
            if not record:
                self.not_found.add(value)
                return False
            else:
                self.dictionary[value] = {}
                for field in record:
                    if field != '_id':
                        self.dictionary[value][field] = record[field]
                self.modified = True
                return True

    def __getitem__(self, value):
        if value not in self.dictionary:
            retv = self.__cache(value)
            if not retv:
                raise KeyError(f'{self.key} : {value} does not exist.')
        return self.dictionary[value]

    def __contains__(self, value):
        local = value in self.dictionary
        if local:
            return True
        else:
            return self.__cache(value)

    def save(self, cache_file):
        if self.modified:
            print('Saving cached data to', cache_file)
            with open(cache_file, 'wb') as f:
                pickle.dump(self.dictionary, f)

    def load(self, cache_file):
        if os.path.isfile(cache_file):
            print('Loading cached data from', cache_file)
            with open(cache_file, 'rb') as f:
                self.dictionary = pickle.load(f)


class OrgTable:
    def __init__(self, *args):
        self.cols = len(args)
        self.header = args
        self.body = []

    def __make_str(self, vals):
        return f'| {" | ".join(vals)} |'

    def add(self, **kwargs):
        vals = []
        for key in self.header:
            if key in kwargs:
                vals.append(kwargs[key])
            else:
                vals.append('')
        self.body.append(tuple(vals))

    def save(self, fname):
        with open(fname, 'w') as outf:
            print(self.__make_str(self.header), file=outf)
            print('|-|', file=outf)
            for line in self.body:
                print(self.__make_str(line), file=outf)

    @staticmethod
    def load(fname):
        def parse_str(line):
            return [
                s.strip()
                for s in line.strip().split('|')
                if s
            ]
        with open(fname, 'r') as inf:
            header = parse_str(inf.readline())
            print(header)
            ot = OrgTable(*header)
            inf.readline()
            for line in inf:
                ot.body.append(tuple(parse_str(line)))
        return ot


class FileArgparser:
    def __init__(self, def_file):
        self.ap = argparse.ArgumentParser()
        self.sps = self.ap.add_subparsers(dest='command')
        self.sps.required = True
        with open(def_file, 'r') as df:
            defdict = ujson.load(df)
        for c in defdict:
            sp = self.sps.add_parser(c)
            defs = defdict[c]
            for d in defs:
                names = []
                ap_opts = defs[d]['ap_opts']
                if defs[d]['optional']:
                    if 'short' in defs[d]:
                        names.append('-' + defs[d]['short'])
                    names.append('--' + d)
                    if (
                        'default' in ap_opts
                        and ap_opts['default'] is not None
                    ):
                        ap_opts['type'] = type(ap_opts['default'])
                else:
                    names.append(d)
                sp.add_argument(*names, **ap_opts)
        self.args = self.ap.parse_args()
        
    def save(self, arg_file):
        with open(arg_file, 'w') as af:
            to_dump = dict(vars(self.args))
            to_dump.pop('command')
            ujson.dump(to_dump, af)

    def load(self, arg_file):
        with open(arg_file, 'r') as af:
            argdict = ujson.load(af)
        for a in argdict:
            if a not in self.args:
                setattr(self.args, a, argdict[a])
            elif argdict[a] != getattr(self.args, a):
                print(
                    f'Setting {a} to new value:',
                    f'{argdict[a]} -> {getattr(self.args, a)}.'
                )

    def remove(self, arg):
        delattr(self.args, arg)


class Pbar:
    def __init__(self, total, width=20):
        self.count = 0
        self.cursor = 0
        self.width = width
        self.total = total
        self._done_char = '█'
        self._pend_char = '░'

    def add(self, n):
        self.count += n
        self.cursor = round(self.count/(self.total/self.width))

    def reset(self):
        self.count = 0
        self.cursor = 0

    def __str__(self):
        done = self._done_char * self.cursor
        pend = self._pend_char * (self.width - self.cursor)
        return f'{done}{pend} {self.count/self.total:.2%}'


class Display:
    def __init__(self, fmt_str):
        self.fmt_str = '\n'.join(
            line.lstrip()
            for line in fmt_str.split('\n')
        )
        attrs = (
            param
            for _, param, _, _ in Formatter().parse(fmt_str)
            if param
        )
        self.values = dict.fromkeys(attrs, '')

    def __enter__(self):
        self.screen = curses.initscr()
        curses.curs_set(0)
        self.update()
        return self

    def __exit__(self, *exc):
        curses.endwin()
        return False

    def __format(self):
        return self.fmt_str.format(**self.values)

    def update(self, **kwargs):
        self.values.update(kwargs)
        self.screen.clear()
        self.screen.addstr(0, 0, self.__format())
        self.screen.refresh()


class Pbar:
    def __init__(self, total, width=20):
        self.count = 0
        self.cursor = 0
        self.width = width
        self.total = total
        self._done_char = '█'
        self._pend_char = '░'

    def add(self, n):
        self.count += n
        self.cursor = round(self.count/(self.total/self.width))

    def reset(self):
        self.count = 0
        self.cursor = 0

    def __str__(self):
        done = self._done_char * self.cursor
        pend = self._pend_char * (self.width - self.cursor)
        return f'{done}{pend} {self.count/self.total:.2%}'


#cache_dir = '.cache'
# TODO cfg somewhere
cache_dir = '/scratch/tmp/disambiguation/cache'


def _cache_fn(function, fmt):
    if fmt == 'json':
        backend = ujson
        opts = {'ensure_ascii': False}
        mode = ''
    elif fmt == 'pck':
        backend = pickle
        opts = {}
        mode = 'b'
    def wrapper(*args, **kwargs):
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        fname = function.__name__
        mname = function.__module__
        cache_name = f'{mname}.{fname}.{fmt}'
        cache_file = os.path.join(cache_dir, cache_name)
        if os.path.isfile(cache_file):
            print('Loading cached data for', fname)
            with open(cache_file, f'r{mode}') as f:
                retv = backend.load(f)
        else:
            print('Saving cache at', cache_file)
            retv = function(*args, **kwargs)
            with open(cache_file, f'w{mode}') as f:
                backend.dump(retv, f, **opts)
        return retv
    return wrapper


pickle_cache = partial(_cache_fn, fmt='pck')
json_cache = partial(_cache_fn, fmt='json')


def memoize(fun):
    results = {}
    def wrapper(*args, **kwargs):
        sig = args + tuple(kwargs.items())
        if sig not in results:
            results[sig] = fun(*args, **kwargs)
        return results[sig]
    return wrapper


def count_lines(fname):
    wproc = sp.run(
        ['wc', '-l', fname],
        stdout=sp.PIPE,
        encoding='utf-8'
    )
    print(wproc.stdout.split(' '))
    return int(wproc.stdout.split(' ')[0])
