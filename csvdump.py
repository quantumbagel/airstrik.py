import time
from datetime import datetime

import pymongo.errors
from pymongo.mongo_client import MongoClient
import argparse
import csv
import sys
import os

parser = argparse.ArgumentParser(prog='csvdump.py',
                                 description='A program to visualize the planes collected by airstrik.py',
                                 epilog='Go Pack!')
parser.add_argument('-d', '--database', help='which database in the mongodb to pull from', required=False)
parser.add_argument('-u', '--uri', default='mongodb://localhost:27017', help='The URI to connect to (mongodb)')
parser.add_argument('-o', '--out', default='out.csv', help="The file to output to")
parser.add_argument('-s', '--stats', action='store_true', help='whether to comb for stats or not')
parser.add_argument('-n', '--no-warn', action='store_true', help='warn about deleting files or not')
args = parser.parse_args()
progress_ht_num = 30
print("Connecting to MongoDB...")
client = MongoClient(args.uri)
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
if args.out in os.listdir():
    if not args.no_warn:
        cont = input("The file " + args.out + ' already exists! Would you like to delete it? (y/n)')
        if cont not in ['y', 'yes']:
            sys.exit(0)
    os.remove(args.out)
if args.stats:
    fieldnames = ['date', 'unique_planes', 'total_trips', 'unique_alarm_planes', 'total_alarm_trips']
    with open(args.out, 'x', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        print()
        lc = [i for i in colnames if i.startswith('stats.')]
        for cur, item in enumerate(lc):
            pct = (cur + 1) / len(lc) * progress_ht_num
            print("Writing", item,
                  "(" + ("#" * int(pct)) + "." * int(progress_ht_num - pct) + ") (" + str(cur + 1) + "/" + str(
                      len(lc)) + ")", flush=True)
            sys.stdout.flush()
            split_item = item.split('.')
            dat = list(db['stats'][split_item[1]].find())
            for i, data in enumerate(dat):
                write_dict = {'date': split_item[1]}
                for it in data.keys():
                    if it == '_id':
                        continue
                    write_dict.update({it: data[it]})
                writer.writerow(write_dict)
else:
    fieldnames = ['name', 'flight_id', 'start_time', 'end_time', 'lat', 'lon', 'nav_heading', 'alt_geom',
                  'calc_heading',
                  'calc_speed', 'distance', 'trip', 'filters']
    with open(args.out, 'x', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        print()
        lc = [i for i in colnames if not i.startswith('stats')]
        for cur, item in enumerate(lc):
            pct = (cur + 1) / len(lc) * progress_ht_num
            print("Writing", item,
                  "(" + ("#" * int(pct)) + "." * int(progress_ht_num - pct) + ") (" + str(cur + 1) + "/" + str(
                      len(lc)) + ")", flush=True)
            sys.stdout.flush()
            dat = list(db[item].find())
            for i, data in enumerate(dat):
                flight_name = data['flight_name_id']
                if flight_name is not None:
                    flight_name = flight_name[0]
                write_dict = {'name': item, 'flight_id': flight_name, 'trip': i + 1}
                for it in data.keys():
                    if it not in ['_id', 'alarm', 'extras', 'flight_name_id', 'filters']:
                        try:
                            write_dict.update({it: data[it][0]})
                        except TypeError:
                            continue
                for it in data['extras'].keys():
                    if it not in ['alarm_triggered', 'commentary']:  # commentary for legacy db
                        write_dict.update({it: datetime.fromtimestamp(data['extras'][it])})
                ftext = ''
                try:
                    for each_filter in data['filters'].keys():
                        each_filter_data = data['filters'][each_filter]
                        ftext += (each_filter + ' (' + str(each_filter_data['dist']) + ', ' + str(each_filter_data['alt']) + '), ')
                    ftext = ftext[:-2]
                    write_dict.update({'filters': ftext})
                except KeyError:
                    print('this instance is not compatible with filters!')
                    write_dict.update({'filters': ''})
                writer.writerow(write_dict)

print("Dumped to", args.out)
print("Stopping MongoDB...")
client.close()
print('done')
