from datetime import datetime

import pymongo.errors
from pymongo.mongo_client import MongoClient
import argparse
import csv
import sys


def delete_last_line(lines=1):
    """
    Delete the number of lines given
    :param lines: The number of lines to delete from stdout
    :return: nothing
    """
    for _ in range(lines):
        sys.stdout.write('\x1b[1A')
        sys.stdout.write('\x1b[2K')

parser = argparse.ArgumentParser(prog='csvdump.py', description='A program to visualize the planes collected by airstrik_mongo.py', epilog='Go Pack!')
parser.add_argument('-d', '--database', help='which database in the mongodb to pull from', required=False)
parser.add_argument('-u', '--uri', default='mongodb://localhost:27017', help='The URI to connect to (mongodb)')
parser.add_argument('-o', '--out', default='out.csv', help="The file to output to")
args = parser.parse_args()
progre_ht_num = 30
print("Connecting to MongoDB...")
client = MongoClient(args.uri)
delete_last_line()
client.admin.command('ping')
all_databases = client.list_database_names()
if (args.database not in all_databases) or (args.database in ['admin', 'config']) or args.database is None:
    print("ERROR: You need to provide a valid database name (-d). Here's a list of those databases:")
    for item in all_databases:
        if item not in ['admin', 'config']:
            print(item)
    sys.exit(0)
db = client[args.database]
colnames = db.list_collection_names()
fieldnames = ['name', 'flight_id', 'start_time', 'end_time', 'lat', 'lon', 'nav_heading', 'alt_geom', 'calc_heading',
              'calc_speed', 'time_until_entry', 'distance', 'trip']
with open(args.out, 'x', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    print()
    for cur, item in enumerate(colnames):
        delete_last_line()
        pct = (cur+1)/len(colnames) * progre_ht_num
        print("Writing", item,
              "("+("#"*int(pct))+"."*int(progre_ht_num-pct)+") ("+str(cur+1)+"/"+str(len(colnames))+")")
        sys.stdout.flush()
        if item == 'stats':
            continue
        dat = list(db[item].find())
        for i, data in enumerate(dat):
            flight_name = data['flight_name_id']
            if flight_name is not None:
                flight_name = flight_name[0]
            write_dict = {'name': item, 'flight_id': flight_name, 'trip': i+1}
            for it in data.keys():
                if it not in ['_id', 'alarm', 'extras', 'flight_name_id']:
                    try:
                        write_dict.update({it: data[it][0]})
                    except TypeError:
                        continue
            for it in data['extras'].keys():
                if it not in ['alarm_triggered', 'commentary']:  # commentary for legacy db
                    write_dict.update({it: datetime.fromtimestamp(data['extras'][it])})
            writer.writerow(write_dict)
