# -*- coding: utf-8 -*

import tensorflow as tf

from .base import BaseModel

class ErDetectModel(BaseModel):
    def build_graph(self):
        with tf.name_scope('read-instances'):
            self.read_instances()

        self.train_instances = self.train_it.get_next()
        train_sents = self.train_instances['sent']
        train_label = self.train_instances['label']

        self.valid_instances = self.valid_it.get_next()
        valid_sents = self.valid_instances['sent']
        valid_label = self.valid_instances['label']


        run_network = tf.make_template(
            'network',
            self.network_template
        )

        train_logits = run_network(train_sents)
        valid_logits = run_network(valid_sents)

        with tf.name_scope('compute-loss'):
            loss = self.compute_loss(
                train_logits,
                train_label,
            )
            self.valid_loss = self.compute_loss(
                valid_logits,
                valid_label
            )
            if self.l2_lambda:
                l2_weights = [
                    tf.nn.l2_loss(v)
                    for v in tf.trainable_variables()
                    if 'bias' not in v.name
                ]
                l2_term = tf.reduce_mean(l2_weights) * self.l2_lambda
                loss = tf.add(loss, l2_term)
                self.valid_loss = tf.add(self.valid_loss, l2_term)


        self.objective = loss


        with tf.name_scope('get-predictions'):
            self.valid_pred, self.raw_valid_pred = self.get_predictions(valid_logits)
            self.train_pred, _ = self.get_predictions(train_logits)

        with tf.name_scope('compute-accuracy'):
            self.accuracy = tf.contrib.metrics.accuracy(
                self.valid_pred,
                valid_label
            )
    
            self.cmatrix = tf.confusion_matrix(
                tf.squeeze(valid_label),
                tf.squeeze(self.valid_pred),
                num_classes=1
            )
            self.train_accuracy = tf.contrib.metrics.accuracy(
               self.train_pred,
               train_label
            )

        optimizer = tf.train.AdamOptimizer(learning_rate=1e-4, epsilon=1e-3)
        self.train_op = optimizer.minimize(
            self.objective,
            global_step=self.global_step,
            name='train-op'
        )
        self.acc_ph = tf.placeholder(tf.float32, shape=[])
        self.trainacc_ph = tf.placeholder(tf.float32, shape=[])
        self.validloss_ph = tf.placeholder(tf.float32, shape=[])

        with tf.name_scope('loss'):
            loss_sc = tf.summary.scalar('train', self.objective)
            validloss_sc = tf.summary.scalar('valid', self.validloss_ph)

        with tf.name_scope('accuracy'):
            trainacc_sc = tf.summary.scalar('train', self.trainacc_ph)
            acc_sc = tf.summary.scalar('valid', self.acc_ph)

        self.train_summaries = tf.summary.merge([trainacc_sc, loss_sc])
        self.valid_summaries = tf.summary.merge([acc_sc, validloss_sc])

    def __init__(
        self,
        vin,
        bsize,
        epochs,
        winsize,
        embed_dim,
        hidden_size,
        attention_size,
        l2_lambda,
        dropout,

    ):
        super().__init__(
            vin,
            bsize,
            epochs,
            winsize,
            embed_dim,
            hidden_size,
            attention_size,
            dropout,
        )
        self.l2_lambda = l2_lambda

        self.build_graph()

        self.saver = tf.train.Saver(
            keep_checkpoint_every_n_hours = 1
        )

        self.init_op = tf.group(
            tf.global_variables_initializer(),
            tf.local_variables_initializer()
        )
