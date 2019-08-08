# -*- coding: utf-8 -*-

from pymongo import MongoClient

dbuser = 'langtools'
dbpass = 'best_password_qwerty123'
dbhost = 'svm-33.cs.helsinki.fi'
dbport = 27062
dbname = 'documents'

def get_db(connect=True, dbname=dbname):
    return MongoClient(f'mongodb://{dbuser}:{dbpass}@{dbhost}:{dbport}', connect=connect)[dbname]


get_db()
