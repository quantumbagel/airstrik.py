import pymongo.errors
from pymongo.mongo_client import MongoClient
import argparse
import csv

parser = argparse.ArgumentParser(prog='csvdump.py', description='A program to visualize the planes collected by airstrik_mongo.py', epilog='Go Pack!')
parser.add_argument('-d', '--database', help='which database in the mongodb to pull from', required=False)
parser.add_argument('-u', '--uri', default='mongodb://localhost:27017', help='The URI to connect to (mongodb)')
parser.add_argument('-o', '--out', default='out.csv', help="The file to output to")
args = parser.parse_args()

print("Connecting to MongoDB...")
client = MongoClient(args.uri)
print("Confirming connection...")
client.admin.command('ping')
print("MongoDB is connected.")
all_databases = client.list_database_names()
if (args.database not in all_databases) or (args.database in ['admin', 'config']) or args.database is None:
    print("ERROR: You need to provide a valid database name (-d). Here's a list of those databases:")
    for item in all_databases:
        if item not in ['admin', 'config']:
            print(item)
db = client[args.database]
colnames = db.list_collection_names()

fieldnames = ['name', 'lat', 'long', 'nav_heading', 'alt_geom', 'calc_heading', 'calc_speed', 'time_until_entry', 'distance']
with open(args.out, 'x', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for item in colnames:
        data = db[item].find()
        write_dict = {'name': item}
        for it in data.keys():
            if it != '_id':
                write_dict.update({it: data[it]})
        writer.writerow(write_dict)