#!/cs/puls/pyenv/shims/python
# -*- coding: utf-8 -*-

import os

import petname
import tensorflow as tf
import numpy as np
from tensorboard import summary as summary_lib
from tensorboard.plugins.custom_scalar import layout_pb2
import csv

from er_detect_model import ErDetectModel
from utils import vocab
from utils import utils

import codecs
windowrad = 10
winsize = (windowrad * 2) + 1


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

language = 'Russian'
surf_vocab = vocab.Vocab.load('/experiments/ErrData/ru/surfaces.txt', language)
lemma_vocab = vocab.Vocab.load('/experiments/ErrData/ru/lemmas.txt', language)

print_every = 100
eval_every = 2000


def new_run_dir():
    run_dir = '/cs/experiments/err_detect/ru/ru_new_run'
    cond = True
    while cond:
        rname = petname.generate(letters=8)
        run_dir = os.path.join(run_dir, rname)
        cond = os.path.isdir(run_dir)
    os.makedirs(run_dir)
    return run_dir


def load_pretrained(sess, model, emb_file):
    pretrained = np.float32(np.load(emb_file))
    sess.run(
        model.set_pretrain,
        feed_dict={model.pretrain_ph: pretrained}
    )


def train_model(sess, model, run_dir, ckp_every=20000, max_steps=-1):
    display.update(run=run_dir, msg='Training model...')
    sum_path = os.path.join(run_dir, 'summaries')
    ckp_path = os.path.join(run_dir, 'checkpoints/model')
    train_writer = tf.summary.FileWriter(
        os.path.join(os.path.join(sum_path, 'train')),
        sess.graph
    )
    valid_writer = tf.summary.FileWriter(
        os.path.join(os.path.join(sum_path, 'valid')),
        sess.graph
    )

    sess.run(
        model.train_it.initializer,
        feed_dict={
            model.train_file: args.input_file,
        }
    )
    step = 0
    closs = 0
    cacc = 0
    n = 0
    summaries = None

    while True:
        try:
            if step == max_steps:
                break
            _, loss, train_acc, step = sess.run([
                model.train_op,
                model.objective,
                model.train_accuracy,
                model.global_step,
            ])
            closs += loss
            cacc += train_acc
            if step % print_every == 0:
                cacc = cacc / print_every
                display.update(step=step, loss=closs / print_every, tacc=cacc)
                summaries = sess.run(
                    model.train_summaries,
                    feed_dict={model.trainacc_ph: cacc}
                )
                closs = 0
                cacc = 0
            if args.evaluate and step % eval_every == 0:
                display.update(msg='Evaluating model...')
                eval_model(sess, model, step, writer=valid_writer)
                display.update(msg='Training model...')
            if step > 0 and step % ckp_every == 0:
                display.update(msg='Saving checkpoint...')
                model.saver.save(
                    sess,
                    ckp_path,
                    global_step=step
                )
                display.update(msg='Training model...')
            if summaries:
                train_writer.add_summary(summaries, step)
        except tf.errors.OutOfRangeError:
            display.update(msg='Validating model...')
            eval_model(sess, model, step, writer=valid_writer)
            if args.test_file:
                display.update(msg='Testing model...')
                eval_model(sess, model, mode='test')
            display.update(msg='Finalazing...')
            display.update(msg='Saving checkpoint...')
            model.saver.save(
                sess,
                ckp_path,
                global_step=step
            )
            display.update(msg='Done.')
            break
        except KeyboardInterrupt:
            display.update(msg='Stopping...')
            break
    train_writer.close()
    valid_writer.close()



def eval_model(sess, model, step=None, writer=None, mode=None, csv_writer=None):
    if mode == 'test':
        sess.run(
            model.valid_it.initializer,
            feed_dict={
                model.valid_file: args.test_file
            }
            
        )
    else:
        sess.run(
            model.valid_it.initializer,
            feed_dict={
                model.valid_file: args.evaluate
            }
        )
    cacc = 0
    closs = 0
    n = 0
    while True:
        try:
            acc, valid_loss = sess.run([
                model.accuracy,
                model.valid_loss
            ])
            cacc += acc
            closs += valid_loss
            n += 1
            
        except tf.errors.OutOfRangeError:
            cacc /= n
            closs /= n
            if mode == 'test':
                display.update(testacc=cacc, tloss=closs)
            else:
                display.update(acc=cacc, vloss=closs)
            if writer:
                summaries = sess.run(
                    model.valid_summaries,
                    feed_dict={
                        model.acc_ph: cacc,
                        model.validloss_ph: closs
                    }
                )
                writer.add_summary(summaries, step)
            break



def infer(sess, model):
    sess.run(
        [
            model.valid_it.initializer
        ],
        feed_dict={
            model.valid_file: args.test_file
        }
    )

    pred = sess.run(
        [
            model.raw_valid_pred
        ]
    )

    print(pred)


def build_model(args):

    model = ErDetectModel(
        len(surf_vocab),
        args.batch_size,
        args.epochs,
        (args.window_radius * 2) + 1,
        args.embed_dim,
        args.lstm_size,
        args.attention_size,
        args.l2_lambda,
        args.dropout,
        )
    return model


if __name__ == '__main__':
    ap = utils.FileArgparser('er_detect_args.json')
    args = ap.args
    scfg = tf.ConfigProto()
    dtxt = (
        '''
        Run path: {run}
        ==========================
        Step: {step}
        Train Loss: {loss}
        Train Accuracy: {tacc}
        --------------------------
        Validation Loss: {vloss}
        Validation Accuracy: {acc}
        --------------------------
        * * * Only when testing final model * * *
        Test Loss: {tloss}
        Test Accuracy: {testacc}
        __________________________
        {msg}
        '''
    )
    with tf.Session(config=scfg) as sess:
        if args.command == 'train':
            run_dir = new_run_dir()
            ap.save(os.path.join(run_dir, 'args.json'))
            print('Building model')
            model = build_model(args)
            sess.run(model.init_op)
            if args.pretrained:
                print('Loading pretrained')
                load_pretrained(sess, model, args.pretrained)
            with utils.Display(dtxt) as display:
                train_model(sess, model, run_dir)
        elif args.command == 'test':
            run_dir = args.run_path
            arg_file = os.path.join(run_dir, 'args.json')
            ap.load(arg_file)
            model = build_model(args)
            print('Building model...')
            model.load(os.path.join(run_dir, 'checkpoints'))
            print('Loading model...')
            with utils.Display(dtxt) as display:
                print('Evaluating...')
                eval_model(sess, model, mode='test')
        elif args.command == 'resume':
            run_dir = args.run_path
            arg_file = os.path.join(run_dir, 'args.json')
            ap.load(arg_file)
            ap.save(os.path.join(run_dir, 'args.json'))
            model = build_model(args)
            print('Loading the model...')
            model.load(os.path.join(run_dir, 'checkpoints'))
            with utils.Display(dtxt) as display:
                train_model(sess, model, run_dir)

        elif args.command == 'infer':
            run_dir = args.run_path
            arg_file = os.path.join(run_dir, 'args.json')
            ap.load(arg_file)
            model = build_model(args)
            print('Building model...')
            model.load(os.path.join(run_dir, 'checkpoints'))
            print('Loading model...')
            infer(sess, model)
