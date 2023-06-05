import json
import math
import os
import subprocess
import sys
import threading
import time
import geopy.distance
DUMP1090_DIR = '/home/jreder/dump1090'
RUN_COLLECT_FOR = 480  # 8 minutes
PREVIEW_SEC = 30
HOME = (35.75124, -78.90223)
RADIUS = 20 # km
SEEN_MAX = 60
OLD_USE_PACKET = 10
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


def start():
    subprocess.run("rm -rf " + DUMP1090_DIR + "/gai", shell=True)
    subprocess.run("mkdir " + DUMP1090_DIR + "/gai", shell=True)
    t = threading.Thread(target=run_dump1090, daemon=True)
    t.start()
    print("Waiting on aircraft.json", end='')
    while 'aircraft.json' not in os.listdir(DUMP1090_DIR + '/gai'):
        print(".", end='')
        time.sleep(0.1)
    print()


def print_the_plane(plane, hex):
    print(hex+": ", end='')
    for item in plane:
        try:
            print(str(plane[item][-1][0])+(len(item)-len(str(plane[item][-1][0]))+1)*' ', end=' ')
        except Exception as e:
            print('NO'+(len(item))*' ', end='')
    print()


def calculate_heading_directions(prev, curr):
    pi_c = math.pi/180
    first_lat = prev[0] * pi_c
    first_lon = prev[1] * pi_c
    second_lat = curr[0] * pi_c
    second_lon = curr[1] * pi_c
    y = math.sin(second_lon - first_lon) * math.cos(second_lat)
    x = (math.cos(first_lat) * math.sin(second_lat)) - (math.sin(first_lat) * math.cos(second_lat) * math.cos(second_lon - first_lon))
    heading_rads = math.atan2(y, x)
    return ((heading_rads * 180 / math.pi) + 360) % 360


if __name__ == '__main__':
    start()
    plane_history = {}
    print("Ready to go.")
    aircrafts_dt = json.load(open(DUMP1090_DIR+'/gai/aircraft.json'))
    current_time_aircraft = float(aircrafts_dt['now'])
    current_time_aircraft -= 1
    stats = ['flight', 'alt_baro', 'nav_heading', 'lat', 'lon']
    print(" " * 8, end='')
    for item in ['flight', 'lat', 'lon', 'nav_heading', 'alt_baro', 'calc_heading', 'calc_speed', 'alarm', 'time_until_entry', 'distance']:
        print(item + " " * 10, end='')
    print()
    for tick in range(RUN_COLLECT_FOR):
        while True:
            aircrafts_dt = json.load(open(DUMP1090_DIR + '/gai/aircraft.json'))
            ncurrent_time_aircraft = float(aircrafts_dt['now'])
            if ncurrent_time_aircraft != current_time_aircraft:
                break
        if tick != 0:
            delete_last_line(lines=last_printed)
        last_printed = 0
        current_time_aircraft = ncurrent_time_aircraft
        key_sorted = [(ind, i['hex']) for ind, i in enumerate(aircrafts_dt['aircraft'])]
        hexes = {i[1]: i[0] for i in key_sorted}
        sorted_hexes = sorted(hexes)
        for hex_v in sorted_hexes:
            aircraft = aircrafts_dt['aircraft'][hexes[hex_v]]
            if aircraft['hex'] not in plane_history.keys():
                plane_history.update({aircraft['hex']: {"flight_name_id": [],
                                                        "lat_history": [],
                                                        "lon_history": [],
                                                        "nav_heading_history": [],
                                                        "alt_baro_history": [],
                                                        "calc_heading_history": [],
                                                        "calc_speed_history": [],
                                                        'alarm_history': [],
                                                        'time_until_entry_history': [],
                                                        'distance_history': []}})
            plane_data = plane_history[aircraft['hex']]
            if not len(plane_data['flight_name_id']):
                if 'flight' in aircraft.keys():
                    plane_data['flight_name_id'] = [0, [aircraft['flight']]]
                    print(plane_data['flight_name_id']*100)
            for item in ['lat', 'lon', 'nav_heading', 'alt_baro']:
                if item in aircraft.keys():
                    if len(plane_data[item+'_history']) and plane_data[item+'_history'][-1][0] == aircraft[item]:
                        print(end='')
                    else:
                        plane_data[item+'_history'].append((float(aircraft[item]), current_time_aircraft))
            if max([len(plane_data['lat_history']), len(plane_data['lon_history'])]) >= 2:

                current_lat_long = plane_data['lat_history'][-1][0], plane_data['lon_history'][-1][0]
                last_lat_long = plane_data['lat_history'][-2][0], plane_data['lon_history'][-2][0]
                if len(plane_data['lat_history']) < OLD_USE_PACKET:
                    use_num = 0
                    oldest_lat_long = plane_data['lat_history'][0][0], plane_data['lon_history'][0][0]
                else:
                    oldest_lat_long = plane_data['lat_history'][-1*OLD_USE_PACKET][0], plane_data['lon_history'][-1*OLD_USE_PACKET][0]
                    use_num = -1*OLD_USE_PACKET
                dist_xz = geopy.distance.geodesic(current_lat_long, oldest_lat_long).m
                time_between = plane_data['lat_history'][-1][1] - plane_data['lat_history'][use_num][1]
                heading_xz = calculate_heading_directions(last_lat_long, current_lat_long)
                ncalc_heading = [heading_xz, plane_data['lat_history'][-1][1]]
                if ncalc_heading not in plane_data['calc_heading_history']:
                    plane_data["calc_heading_history"].append(ncalc_heading)
                ncalc_speed = [dist_xz/time_between * 3.6, plane_data['lat_history'][-1][1]]
                if ncalc_speed not in plane_data['calc_speed_history']:
                    plane_data["calc_speed_history"].append(ncalc_speed)
                lat_change_sec = (current_lat_long[0] - last_lat_long[0])/time_between
                long_change_sec = (current_lat_long[1] - last_lat_long[1])/time_between
                min_radius = 100000000
                dt_time = max(plane_data['lat_history'][-1][1], plane_data['lon_history'][-1][1])
                date_old = current_time_aircraft - dt_time
                alarm_time = -1
                alarm = False
                last_radius = 100000000
                for second in range(PREVIEW_SEC):
                    new_lat = lat_change_sec * (second+1) + current_lat_long[0]
                    new_long = long_change_sec * (second+1) + current_lat_long[1]
                    new_coords = (new_lat, new_long)
                    dist_to_home = geopy.distance.geodesic(new_coords, HOME).km
                    alarm_lat_long = dist_to_home < RADIUS
                    if alarm_lat_long:
                        alarm = True
                        if alarm_time == -1:
                            alarm_time = second
                        if dist_to_home < min_radius:
                            min_radius = dist_to_home
                        if dist_to_home > last_radius:
                            break
                        last_radius = dist_to_home

                plane_data['alarm_history'].append([alarm, current_time_aircraft])
                if alarm_time == -1:
                    inp = 'NO'
                else:
                    inp = alarm_time - date_old
                plane_data['time_until_entry_history'].append([inp, current_time_aircraft])
            if min([len(plane_data['lat_history']), len(plane_data['lon_history'])]) >= 1:
                current_lat_long = plane_data['lat_history'][-1][0], plane_data['lon_history'][-1][0]
                dt_time = max(plane_data['lat_history'][-1][1], plane_data['lon_history'][-1][1])
                ndistance = [geopy.distance.geodesic(HOME, current_lat_long).km, dt_time]
                if dt_time not in plane_data['distance_history']:
                    plane_data['distance_history'].append(ndistance)

        def get_distance(d):
            try:
                return d['distance_history'][-1][0]
            except IndexError:
                return 10000
        def is_not_empty(d):
            for key in d.keys():
                if len(d[key]):
                    return True
            return False
        sorted_dist = sorted(plane_history.values(), key=get_distance)
        for item in sorted_dist:
            try:
                hex_code = list(plane_history.keys())[list(plane_history.values()).index(item)]
            except KeyError: # aircraft no longer exists
                continue

            if (aircrafts_dt['aircraft'][hexes[hex_code]]['seen'] < SEEN_MAX) and is_not_empty(item):
                print_the_plane(item, hex_code)
                last_printed += 1


    if os.path.exists("/home/jreder/PycharmProjects/ADS-B/dump.json"):
        os.remove("/home/jreder/PycharmProjects/ADS-B/dump.json")
    json.dump(plane_history, open('/home/jreder/PycharmProjects/ADS-B/dump.json', 'x'), indent=4, sort_keys=True)
    print('done.')
