#!/bin/sh



#python3 ./run_er_detect.py train /experiments/ErrData/ru/new_data/train.tfrecord -e experiments/ErrData/ru/new_data/valid.tfrecord -p experiments/ErrData/ru/new_data/form_pretrained_300.npy


python3 ./run_er_detect.py resume /experiments/err_detect/ru/ru_new_run/happy-starfish

