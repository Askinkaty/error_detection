# -*- coding: utf-8 -*-

from fastai.text import *
import os

import torch
from fastai.text import LanguageLearner

torch.cuda.set_device(0)

from fastai.callbacks import SaveModelCallback, ReduceLROnPlateauCallback


def download_text(path, data_file, bs):
    if os.path.exists('../Russian-ULMFit/'+ data_file):
        print('Loading data...')
        data = load_data('.', '../Russian-ULMFit/rus_norm_data', bs=bs)
    else:
        print('Collecting data from directory...')
        n = 0
        texts = list()
        for root, _, files in (os.walk(path)):
            print(len(files))
            for file in files:
                n += 1
                if n == 149700:
                    break
                with open(os.path.join(root, file)) as f:
                    texts.append(f.read().strip())
                    print(len(texts))
        texts = pd.DataFrame(texts)
        bs = 64
        data = TextList.from_df(texts,
                                processor=[TokenizeProcessor(tokenizer=Tokenizer(lang="xx")),
                                           NumericalizeProcessor(min_freq=2, max_vocab=60000)]). \
            random_split_by_pct(.1). \
            label_for_lm(). \
            databunch(bs=bs)
        data.save('rus_norm_data')
    return data


def fit_model(learn, epoch, learner_saved, encoder_saved):
    if learner_saved and encoder_saved:
        learn.load(learner_saved)
        learn.load_encoder(encoder_saved)
    learn.fit_one_cycle(epoch, 2e-3, moms=(0.8, 0.7),
                        callbacks=[SaveModelCallback(learn), ReduceLROnPlateauCallback(learn, factor=0.8)])
    leaner_to_save = "lm_" + str(epoch) + "_ep_lr2-3Px"
    encoder_to_save = "lm_" + str(epoch) + "_ep_lr2-3_encx"
    learn.save(leaner_to_save)
    learn.save_encoder(encoder_to_save)
    return learn, leaner_to_save, encoder_to_save


def beam_search(self, text:str, n_words:int, no_unk:bool=True, top_k:int=10, beam_sz:int=1000, temperature:float=1.,
                sep:str=' ', decoder=decode_spec_tokens):
    "Return the `n_words` that come after `text` using beam search."
    ds = self.data.single_dl.dataset
    self.model.reset()
    xb, yb = self.data.one_item(text)
    nodes = None
    xb = xb.repeat(top_k, 1)
    nodes = xb.clone()
    scores = xb.new_zeros(1).float()
    with torch.no_grad():
        for k in progress_bar(range(n_words), leave=False):
            out = F.log_softmax(self.model(xb)[0][:,-1], dim=-1)
            if no_unk: out[:,self.data.vocab.stoi[UNK]] = -float('Inf')
            values, indices = out.topk(top_k, dim=-1)
            scores = (-values + scores[:,None]).view(-1)
            indices_idx = torch.arange(0,nodes.size(0))[:,None].expand(nodes.size(0), top_k).contiguous().view(-1)
            sort_idx = scores.argsort()[:beam_sz]
            scores = scores[sort_idx]
            nodes = torch.cat([nodes[:,None].expand(nodes.size(0),top_k,nodes.size(1)),
                            indices[:,:,None].expand(nodes.size(0),top_k,1),], dim=2)
            nodes = nodes.view(-1, nodes.size(2))[sort_idx]
            self.model[0].select_hidden(indices_idx[sort_idx])
            xb = nodes[:,-1][:,None]
    if temperature != 1.: scores.div_(temperature)
    node_idx = torch.multinomial(torch.exp(-scores), 1).item()
    return text + sep + sep.join(decoder(self.data.vocab.textify([i.item() for i in nodes[node_idx][1:] ], sep=None)))


def my_predict(self, t:str, no_unk:bool=True, temperature:float=1., min_p:float=None, sep:str=' ',
            decoder=decode_spec_tokens):
    self.model.reset()
    words = t.split(' ')
    first = words[0]
    xb,yb = self.data.one_item(first)
    next_ids = []
    predictions = []
    for i, w in enumerate(words[1:]):
        res = self.pred_batch(batch=(xb,yb))[0][-1]
        next_w_ind = self.data.vocab.stoi[w]
        if no_unk: res[self.data.vocab.stoi[UNK]] = 0.
        if min_p is not None:
            if (res >= min_p).float().sum() == 0:
                warn(f"There is no item with probability >= {min_p}, try a lower value.")
            else: res[res < min_p] = 0.
        if temperature != 1.: res.pow_(1 / temperature)
        pred = res[next_w_ind]
        predictions.append(pred)
        idx = next_w_ind
        next_ids.append(idx)
        xb = xb.new_tensor([idx])[None]
    return first + sep + sep.join(decoder(self.data.vocab.textify(next_ids, sep=None))), float(sum(predictions))


if __name__ == '__main__':
    path = "/cs/experiments/Taiga/Taiga_part"
    data_file = 'rus_norm_data'
    bs = 64
    data = download_text(path, data_file, bs)
    learn: LanguageLearner = language_model_learner(data, arch=AWD_LSTM, pretrained=False)
    learn.unfreeze()
    learn.lr_find()
    learn.recorder.plot()
    learn, learner_saved, encoder_saved = fit_model(learn, 1)

    #type(learn).predict = my_predict
    #learn.predict('Прийти домой рано')
    #learn.predict('Прийти дому рано')