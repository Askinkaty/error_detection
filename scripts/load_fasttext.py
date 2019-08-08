#!/cs/puls/pyenv/shims/python
# -*- coding: utf-8 -*-

import numpy as np
from tqdm import tqdm
from gensim.models import FastText
from sklearn.decomposition import PCA

from disambiguation import vocab
from disambiguation import utils

src_dim = 300
dst_dim = 300

surf_file = '/scratch/tmp/disambiguation/surfaces.txt'
total = utils.count_lines(surf_file)
print('Loading Fasttext vectors...')
model = FastText.load_fasttext_format('/scratch/tmp/cc.fi.300.bin')
mapped = np.empty([total, src_dim])

print('Mapping...')
rand = 0
with open(surf_file, 'r') as f:
    for i, word in enumerate(tqdm(f, total=total)):
        # Padding is all zeroes
        if word == vocab.padding_label:
            mapped[i] = np.zeros(src_dim)
            continue
        try:
            mapped[i] = model.wv[word]
        except KeyError:
            mapped[i] = np.random.randn(src_dim)
            rand += 1

print(f'{rand/total:.2%} initialized randomly.')

if src_dim != dst_dim:
    print(f'Applying PCA ({src_dim} -> {dst_dim})...')
    pca = PCA(n_components=dst_dim)
    mapped = pca.fit_transform(mapped)

print('Saving to disk...')
np.save(f'/scratch/tmp/disambiguation/pretrained_{dst_dim}', mapped)

print('Done!')
