import os
import subprocess
import sys
import threading
import time
import json
DUMP1090_DIR = '/home/jreder/dump1090'
HEADER = 'HEX    FLIGHT  CAT LAT        LON       SEEN HDG'


def delete_last_line(lines=1):
    for _ in range(lines):
        sys.stdout.write('\x1b[1A')
        sys.stdout.write('\x1b[2K')


def run_dump1090():
    os.chdir(DUMP1090_DIR)
    try:
        p = subprocess.Popen("exec ./dump1090 --write-json gai", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except KeyboardInterrupt:
        p.kill()


def print_ac_data(aircraft):
    hex = aircraft['hex']
    if 'flight' not in aircraft.keys():
        flight = ' '*8
    else:
        flight = aircraft['flight']
    if 'category' not in aircraft.keys():
        category = '  '
    else:
        category = aircraft['category']
    if 'lat' not in aircraft.keys():
        lat = ' '*10
    else:
        lat = str(aircraft['lat'])
        lat += ' '*(10-len(lat))
    if 'lon' not in aircraft.keys():
        lon = ' '*10
    else:
        lon = str(aircraft['lon'])
        lon += ' '*(10-len(lon))
    if 'nav_heading' not in aircraft.keys():
        heading = ' '*4
    else:
        heading = str(aircraft['nav_heading'])
        heading += ' '*(4-len(heading))
    if aircraft['seen'] < 60:
        return hex+' '+flight+' '+category+' '+lat+' '+lon+' '+str(aircraft['seen'])+' '+heading
    else:
        return ''


subprocess.run("rm -rf "+DUMP1090_DIR+"/gai", shell=True)
subprocess.run("mkdir "+DUMP1090_DIR+"/gai", shell=True)
t = threading.Thread(target=run_dump1090, daemon=True)
t.start()
time.sleep(1)
print("Waiting on aircraft.json", end='')

while 'aircraft.json' not in os.listdir(DUMP1090_DIR+'/gai'):
    print(".", end='')
print()

while True:
    time.sleep(1)
    aircrafts_dt = json.load(open(DUMP1090_DIR+'/gai/aircraft.json'))
    print("Now:", aircrafts_dt['now'])
    print("Messages received:", aircrafts_dt['messages'])
    aircrafts = aircrafts_dt['aircraft']
    print(HEADER)
    printed = 0
    for aircraft in aircrafts:
        p = print_ac_data(aircraft)
        if p:
            print(p)
            printed += 1
    delete_last_line(printed+3)


