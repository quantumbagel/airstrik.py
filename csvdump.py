import pymongo.errors
from pymongo.mongo_client import MongoClient
import argparse


parser = argparse.ArgumentParser(prog='csvdump.py', description='A program to visualize the planes collected by airstrik_mongo.py', epilog='Go Pack!')
parser.add_argument('-d', '--database', help='which database in the mongodb to pull from', required=True)
parser.add_argument('-u', '--uri', default='mongodb://localhost:27017', help='The URI to connect to (mongodb)')
args = parser.parse_args()

print("Connecting to MongoDB...")
client = MongoClient(args.uri)
print("Confirming connection...")
client.admin.command('ping')
print("MongoDB is connected.")
all_databases = client.list_database_names()
if (args.database not in all_databases) or (args.database in ['admin', 'config']):
    print("ERROR: You need to provide a valid database name. Here's a list of those databases:")
    for item in all_databases:
        if item not in ['admin', 'config']:
            print(item)
db = client[args.database]
for col in db.list_collection_names():
    print(col)
