# -*- coding: utf-8 -*

import os
import tensorflow as tf
from tensorflow.contrib.rnn import GRUCell
from tensorflow.contrib.rnn import LSTMCell
from tensorflow.python.ops.rnn import bidirectional_dynamic_rnn as bi_rnn
from .attention import attention


class BaseModel:
    def _parse(self, example):
        features = {
            'sent': tf.FixedLenFeature(
                shape=[self.winsize],
                dtype=tf.int64
            ),
            'label': tf.FixedLenFeature(
                shape=[1],
                dtype=tf.int64
            )
        }
        parsed = tf.parse_single_example(example, features)
        return parsed


    def read_instances(self):
        self.train_file = tf.placeholder(tf.string, shape=[])
        train_data = tf.data.TFRecordDataset(self.train_file)
        train_data = train_data.shuffle(10000)
        train_data = train_data.repeat(self.epochs)
        train_data = train_data.map(
            self._parse,
            num_parallel_calls=os.cpu_count() // 2
        )
        train_data = train_data.batch(self.bsize)
        train_data = train_data.prefetch(1)
        self.train_it = train_data.make_initializable_iterator()

        self.valid_file = tf.placeholder(tf.string, shape=[])
        valid_data = tf.data.TFRecordDataset(self.valid_file)
        valid_data = valid_data.shuffle(10000)
        valid_data = valid_data.map(
            self._parse,
            num_parallel_calls=os.cpu_count() // 2
        )
        valid_data = valid_data.batch(self.bsize)
        valid_data = valid_data.prefetch(1)
        self.valid_it = valid_data.make_initializable_iterator()


    def get_embeddings(self, instances, in_W):
        embed_mat = tf.nn.embedding_lookup(in_W, instances)
        return embed_mat


    def build_bilstm(self, embed):
        embed.set_shape(
            [None, self.winsize, self.embed_dim]
        )
#         rnn_outputs, _ = bi_rnn(LSTMCell(self.lstm_hidden_size), LSTMCell(self.lstm_hidden_size),
#                                 inputs=embed, dtype=tf.float32)
#         # Attention layer
#         with tf.name_scope('Attention_layer'):
#             attention_output, alphas = attention(rnn_outputs, self.attention_size, return_alphas=True)
#             tf.summary.histogram('alphas', alphas)
#         drop = tf.nn.dropout(attention_output, self.dropout)
        bilstm = tf.contrib.cudnn_rnn.CudnnLSTM(
            1,
            self.lstm_hidden_size,
            direction='bidirectional',
            dropout=self.dropout
        )
        return bilstm(embed)[0]
        #return drop

    def build_mlp(self, context):
        # Flatten BiLSTM outputs for every word (21)
        flat_context = tf.contrib.layers.flatten(context)
        hidden_layer = tf.contrib.layers.fully_connected(
            flat_context,
            self.mlp_hidden_size,
            activation_fn=tf.nn.leaky_relu
        )
        output_layer = tf.contrib.layers.fully_connected(
            hidden_layer,
            1,
            activation_fn=None
        )
        return output_layer


    def compute_loss(self, logits, labels):
        labels = tf.to_float(labels, name='ToFloat')
        loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=labels,
                                                        logits=logits)
        loss = tf.reduce_mean(loss)
        return loss


    def get_predictions(self, logits):
        raw_pred = tf.nn.sigmoid(logits)
        pred = tf.cast(tf.round(tf.nn.sigmoid(logits)), tf.int64)
        return pred, raw_pred

    def network_template(self, instances):
        # Input weight matrix
        in_W = tf.get_variable(
            'input-weights',
            [self.vin, self.embed_dim],
            initializer=tf.contrib.layers.xavier_initializer(),
            trainable=True
        )
        # Placeholder to plug in pretrained embeddings
        self.pretrain_ph = tf.placeholder(
            tf.float32,
            shape=[self.vin, self.embed_dim]
        )
        self.set_pretrain = tf.assign(in_W, self.pretrain_ph)
        with tf.name_scope('get-embeddings'):
            embeddings = self.get_embeddings(instances, in_W)

        with tf.name_scope('LSTM'):
            context = self.build_bilstm(embeddings)

        with tf.name_scope('MLP'):
            mlp = self.build_mlp(context)
        return mlp


    # Load a model from a checkpoint
    def load(self, model_path):
        ckp = tf.train.latest_checkpoint(model_path)
        if ckp is None:
            print('No checkpoints in the given directory.')
            exit(0)
        # We don't want the old graph, just rebuild it
        sess = tf.get_default_session()
        self.saver.restore(sess, ckp)


    def __init__(
            self,
            vin,
            bsize,
            epochs,
            winsize,
            embed_dim,
            hidden_size,
            attention_size,
            dropout
    ):
        self.global_step = tf.get_variable(
            'global-step',
            shape=[],
            dtype=tf.int64,
            initializer=tf.constant_initializer(0),
            trainable=False
        )
        self.vin = vin
        self.bsize = bsize
        self.epochs = epochs
        self.winsize = winsize
        self.embed_dim = embed_dim
        self.lstm_hidden_size = hidden_size
        self.attention_size = attention_size
        self.mlp_hidden_size = 2 * hidden_size
        self.dropout = dropout
