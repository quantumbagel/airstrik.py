import json
import os
import pprint
import sys
import traceback
from pymongo import errors
from pymongo.mongo_client import MongoClient
print("Connecting to local mongodb... (if this hangs run systemctl start mongod)")
client = MongoClient("mongodb://localhost:27017")
client.admin.command('ping')
current_db = 'Jun9-1090'
last_planes = []


def list_command(thing):
    global current_db
    global last_planes
    if not len(thing):
        if current_db is not None:
            thing = 'db/'+current_db
        else:
            print("Set a database with use first!")
            return
    else:
        thing = thing[0]

    if thing in ['db', 'dbs', 'database', 'databases']:

        dbs = list(client.list_databases())
        for db in dbs:
            print(db['name']+":", "size="+str(db['sizeOnDisk']))
    if thing.startswith('db/'):
        cols = list(client.get_database(thing.replace('db/', '')).list_collections())
        for col in cols:
            print(col['name'])
        last_planes = [col['name'] for col in cols]
    if thing.startswith('plane/'):
        if current_db is None:
            print("Set a database with use first!")
            return
        o = list(client[current_db][thing.replace('plane/', '')].find())
        fid = 'no flight id given'
        l = 0
        for a in o:
            l += 1
            if len(a['flight_name_id']):
                fid = a['flight_name_id'][0][0][:-1]
            print("Trip", str(l)+":", a['commentary'])

        print("Aircraft "+thing.replace('plane/', ''), "("+fid+')', 'made', l, 'trips.')
        print('\nMessages Received')
        for ind, trip in enumerate(o):
            print("Trip", ind+1)
            for item in trip.keys():
                if item in ['_id', 'start_time', 'end_time', 'commentary']:
                    continue
                print(item.replace('_history', '')+":", len(list(trip[item])))


def packet_command(args):
    pass
def reset_command(args):
    global current_db
    print("Are you sure you want to reset the database?")
    i = input("Type exactly this: \"I understand what will happen, and I consent to resetting the database.\"")
    if i == 'I understand what will happen, and I consent to resetting the database.':
        current_db = None
    else:
        print("Does not match.")
        return
    for table in list(client.list_database_names()):
        try:
            client.drop_database(table)
        except errors.OperationFailure:
            print("failed to drop", table)


def search_command(params):
    global current_db
    searchable = {'alt': 'alt_geom_history', 'dist': 'distance_history', 'alarm': 'alarm_history'}
    arg = {'>': lambda x, y: x > y, '<': lambda x, y: x < y, '=': lambda x, y: x == y, '>=': lambda x, y: x >= y}
    must_satisfy = []
    for param in params:
        for src in searchable.keys():
            if param.startswith(src):
                argument = src
                param = param.replace(src, '')
                op = ''
                for ar in arg.keys():
                    if ar in param:
                        if len(ar) > len(op):
                            op = ar
                val = float(param.replace(op, ''))
                must_satisfy.append([argument, arg[op], val])
    cols = list(client[current_db].list_collection_names())
    planes_match = []
    for col in cols:
        things = list(client[current_db][col].find())[0]
        ok = True
        mt = {}
        for i, must in enumerate(must_satisfy):
            t_mt = []
            values = things[searchable[must[0]]]
            fnd = False
            for val in values:
                if must[1](val[0], must[2]):
                    #print(col, val, must[2])
                    t_mt.append(val[1])
                    fnd = True
            mt.update({i: t_mt})
            if not fnd:
                ok = False

        inter = set(mt[0])
        for mo in list(mt.values())[1:]:
            inter = inter & set(mo)
        inter = list(inter)
        if len(inter):
            print(col)
            planes_match.append(col)
    global last_planes
    last_planes = planes_match[:]


def dump_command(arg):
    if len(arg) == 0:

        for item in last_planes:
            th = list(client[current_db][item].find())[0]
            pprint.pprint(th)
    if len(arg) == 1:
        if '.' in arg[0]:
            if os.path.exists(arg[0]):
                os.remove(arg[0])
            f = open(arg[0], 'x')
            thin = {}
            for item in last_planes:
                th = list(client[current_db][item].find())[0]
                del th['_id']
                thin.update({item: th})
            json.dump(thin, f, indent=4, sort_keys=True)
            print("Dumped", len(last_planes), "planes to", arg[0])
            f.close()
        else:
            pprint.pprint(list(client[current_db][arg[0]].find())[0])
    elif len(arg) == 2:
        if os.path.exists(arg[1]):
            os.remove(arg[1])
        f = open(arg[1], 'x')
        th = list(client[current_db][arg[0]].find())[0]
        del th['_id']
        json.dump(th, f, indent=4, sort_keys=True)
        f.close()



def drop_command(table):
    table = table[0]
    if table not in list(client.list_database_names()):
        print("ERR: table doesn't exist")
        return
    chk = input("To drop this table, enter its name: ")
    if chk == table:
        try:
            client.drop_database(table)
        except errors.OperationFailure:
            print("failed to drop table: operation failure (tried to drop admin?)")
    else:
        print('abort')


def use_command(db):
    global current_db
    if len(db) == 0:
        print("Using database", current_db)
        return
    current_db = db[:][0]


command = {'list': {'args': 1, 'help': 'List something (db/database) to list database, or type plane/<db name> to list collections, or col/<collection> to list data in a collection', 'cmd': list_command},
           'use': {'args': 1, 'help': '', 'cmd': use_command},
           'reset': {'cmd': reset_command},
           'drop': {'cmd': drop_command},
           'search': {'cmd': search_command},
           'dump': {'cmd': dump_command},
           'packet': {'cmd': packet_command},
           'exit': {'cmd': lambda ags: sys.exit(0)}}


while True:
    prompt = input("> ")
    if not prompt:
        continue
    cmds = prompt.split(' & ')
    for cmd in cmds:
        args = cmd.split(' ')
        try:
            command[args[0]]['cmd'](args[1:])
        except Exception as err:
            print('failed')
            print(traceback.print_exc())
