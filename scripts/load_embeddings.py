#!/cs/puls/pyenv/shims/python
# -*- coding: utf-8 -*-

import numpy as np
from sklearn.decomposition import PCA
from disambiguation.vocab import Vocab

embeddings = '/cs/puls/Resources/embeddings/Finnish/fin-word2vec.txt'
target_dim = 300

print('Loading vocabulary...')
lemma_vocab = Vocab.load('surfaces.txt')

nwords = len(lemma_vocab) - 1

out_emb = np.ndarray(
    shape=(nwords, target_dim),
    dtype=float
)

valid_words = {}

with open(embeddings, 'r') as f:
    print('Reading embeddings...')
    fl = f.readline().split(' ')
    vnum = int(fl[0])
    vdim = int(fl[1])
    #words = []
    vectors = np.ndarray(shape=(vnum,vdim), dtype=float)
    for i, l in enumerate(f):
        line = l.split(' ')
        word = line[0]
        vectors[i] = np.array(line[1:])
        if word == '<NUM>':
            word = 'NUMBER'
        if word in lemma_vocab.word2index:
            valid_words[word] = i
        #words.append(word)
        if i % 100 == 0:
            print('\rProgress: {:.2%}'.format(i/vnum), end='')
    print()

# print(len(valid_words))
# print('Running PCA...')
# pca = PCA(n_components=target_dim)
# vectors = pca.fit_transform(vectors)

#np.save('./cache/pca', vectors)
rand = 0
print('Assigning the embeddings...')
for index in range(nwords):
    word = lemma_vocab[index + 1]
    if word in valid_words:
        vector = vectors[valid_words[word]]
    else:
        print(word)
        input()
        vector = np.random.randn(target_dim)
        rand += 1
    out_emb[index] = vector
    # if index % 100 == 0:
    #     print('\rProgress: {:.2%}'.format(index/nwords), end='')
print()
print('{:.2%} initialized randomly.'.format(rand/nwords))
np.save(f'pretrained_embeddings_s2s_{target_dim}', out_emb)
