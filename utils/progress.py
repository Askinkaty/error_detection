# -*- coding: utf-8 -*-

import sys
import math

'''
Display progress percentage for multi-process tasks.
'''
def multip(count, total, step):
    step = math.ceil(total / 10000)
    with count.get_lock():
        count.value += 1
    c = count.value
    if c % step == 0:
        print('\rProgress: {:.2%}'.format(c/total), end='')
        sys.stdout.flush()

'''
Display progress percentage for single-process tasks.
'''
def singlep(count, total, step):
    if count % step == 0:
        print('\rProgress: {:.2%}'.format(count/total), end='')
