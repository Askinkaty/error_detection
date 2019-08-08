# Error_detection

This repository contains a part of the code for experiments with detecting grammaticality described in the paper "Multiple Admissibility in Language Learning: Judging Grammaticality Using Unlabeled Data" 
https://www.aclweb.org/anthology/W19-3702 

* [err_detect_model](https://github.com/Askinkaty/error_detection/blob/master/err_detect_model) contains TensorFlow implementation of the model.  
* [err_detect_pt](https://github.com/Askinkaty/error_detection/tree/master/err_detect_pt) is a directory with a Pytorch implementation which is a work in progress. 
* [err_detect_scripts](https://github.com/Askinkaty/error_detection/tree/master/err_detect_scripts) has a part of the code for generating an artificial dataset with grammatical errors for training a model ([generate_err_data.py](https://github.com/Askinkaty/error_detection/blob/master/err_detect_scripts/generate_err_data.py)) and the code for training a fastai AWD LSTM Language Model ([]()) for evaluating the probability of a sentence with alternative grammatical forms and grammatical errors.  

Some code cannot be shared because it is a part of the codebase of an online learning system Revita.
