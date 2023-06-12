import pymongo.errors
from pymongo.mongo_client import MongoClient

# uri = "mongodb://jjreder:airstrikdb@ac-xe0hbtv-shard-00-00.o9kvdxy.mongodb.net:27017,ac-xe0hbtv-shard-00-01.o9kvdxy.mongodb.net:27017,ac-xe0hbtv-shard-00-02.o9kvdxy.mongodb.net:27017/?ssl=true&replicaSet=atlas-4y1pid-shard-0&authSource=admin&retryWrites=true&w=majority"
uri = 'mongodb://localhost:27017'


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
