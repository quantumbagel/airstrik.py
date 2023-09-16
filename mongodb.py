import pymongo.errors
from pymongo.mongo_client import MongoClient


class MongoDBClient:
    def __init__(self, uri, db):
        self.client = MongoClient(uri)
        self.client.admin.command('ping')
        self.database = self.client[db]

    def write(self, hex, time, field, value):
        collection = self.database[hex][field]
        post = {'value': value, 'time': time, '_id': field+str(value)+str(time)}
        try:
            return collection.insert_one(post)
        except pymongo.errors.DuplicateKeyError:
            return None
