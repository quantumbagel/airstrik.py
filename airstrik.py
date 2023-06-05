import json
import math
import os
import subprocess
import sys
import threading
import time
import geopy.distance
import atexit
import argparse
import ruamel.yaml

parser = argparse.ArgumentParser(prog='airstrik.py', description='A simple program to track and detect airplanes '
                                                                 'heading towards the AERPAW field.', epilog='Go Pack!')
parser.add_argument('-q', '--quiet', action='store_true')
parser.add_argument('-c', '--config', default='config.yaml', help='The config file\'s location (yaml). ')
parser.add_argument('--no-dump', help='Don\'t dump to json. NOTE: if config\'s run_for property is indefinite,'
                                      ' this will be ignored', action='store_true')
args = parser.parse_args()
config_file = ruamel.yaml.YAML()
CONFIG = config_file.load(open(args.config))
HOME = (CONFIG['home']['lat'], CONFIG['home']['lon'])


def delete_last_line(lines=1):
    """
    Delete the number of lines given
    :param lines: The number of lines to delete from stdout
    :return: nothing
    """
    for _ in range(lines):
        sys.stdout.write('\x1b[1A')
        sys.stdout.write('\x1b[2K')


def run_dump1090():
    """
    Run dump1090 as a daemon subprocess
    :return: None
    """
    os.chdir(CONFIG['dump1090_dir'])
    p = subprocess.Popen("exec ./dump1090 --write-json airstrik_data --write-json-every "+str(CONFIG['json_speed']), shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.PIPE)
    atexit.register(p.terminate)


def start():
    """
    A function to remove the output directory and recreate it, and wait for dump1090 to start
    :return: none
    """
    subprocess.run("rm -rf " + CONFIG['dump1090_dir'] + "/airstrik_data", shell=True)
    subprocess.run("mkdir " + CONFIG['dump1090_dir'] + "/airstrik_data", shell=True)
    t = threading.Thread(target=run_dump1090, daemon=True)
    t.start()
    print("Loading...", end='')
    sys.stdout.flush()
    while 'aircraft.json' not in os.listdir(CONFIG['dump1090_dir'] + '/airstrik_data'):
        print(".", end='')
        sys.stdout.flush()
        time.sleep(0.1)
    print()


def print_the_plane(plane, hex):  # move to Plane?
    """
    Print one plane's datd
    :param plane: The plane's data
    :param hex: The hex value of the aircraft
    :return: nothing
    """
    print(hex + ": ", end='')
    for item in plane:
        try:
            print(str(plane[item][-1][0]) + (len(item) - len(str(plane[item][-1][0])) + 1) * ' ', end=' ')
        except Exception as e:
            print('NO' + (len(item)) * ' ', end='')
    print()


def calculate_heading_directions(prev, curr):
    """
    A function to calculate heading.
    :param prev: The previous position (lat/long)
    :param curr: The current position (lat/long)
    :return: The heading
    """
    pi_c = math.pi / 180
    first_lat = prev[0] * pi_c
    first_lon = prev[1] * pi_c
    second_lat = curr[0] * pi_c
    second_lon = curr[1] * pi_c
    y = math.sin(second_lon - first_lon) * math.cos(second_lat)
    x = (math.cos(first_lat) * math.sin(second_lat)) - (
                math.sin(first_lat) * math.cos(second_lat) * math.cos(second_lon - first_lon))
    heading_rads = math.atan2(y, x)
    return ((heading_rads * 180 / math.pi) + 360) % 360


def load_aircraft_json(current_time_aircraft):
    """
    A function to wait for json updates, and return them
    :param current_time_aircraft: The current aircraft time
    :return: The new json, and new time
    """
    while True:
        aircraft_json = json.load(open(CONFIG['dump1090_dir'] + '/airstrik_data/aircraft.json'))
        new_current_time_aircraft = float(aircraft_json['now'])
        if new_current_time_aircraft != current_time_aircraft:
            break
    return aircraft_json, new_current_time_aircraft


def patch_add(aircraft, val_name, data):
    """
    Add data to aircraft dictionaries, and check for its uniqueness
    :param aircraft: Aircraft data
    :param val_name: The data's key
    :param data: The data itself
    :return: nothing
    """
    if data not in aircraft[val_name]:
        aircraft[val_name].append(data)


def get_alarm_info(current_lat_long, last_lat_long, time_between, plane_data):
    """
    Calculate the alarm information by simulating the plane given in plane_data
    :param current_lat_long: The current lat/long of the plane
    :param last_lat_long: The last lat/long of the plane
    :param time_between: The time between these two pairs of lat/long
    :param plane_data: the data for the plane
    :return: whether the alarm should be raised, the time we have, and how close to the center it will get,
     as well as when this was updated
    """
    lat_change_sec = (current_lat_long[0] - last_lat_long[0]) / time_between
    long_change_sec = (current_lat_long[1] - last_lat_long[1]) / time_between
    min_radius = 100000000
    packet_time = max(plane_data['lat_history'][-1][1], plane_data['lon_history'][-1][1])
    alarm_time = -1
    alarm = False
    last_radius = 100000000
    for second in range(CONFIG['think_ahead']):
        new_lat = lat_change_sec * (second + 1) + current_lat_long[0]
        new_long = long_change_sec * (second + 1) + current_lat_long[1]
        new_coords = (new_lat, new_long)
        dist_to_home = geopy.distance.geodesic(new_coords, HOME).km
        alarm_lat_long = dist_to_home < CONFIG['radius']
        if alarm_lat_long:
            alarm = True
            if alarm_time == -1:
                alarm_time = second
            if dist_to_home < min_radius:
                min_radius = dist_to_home
            if dist_to_home > last_radius:
                break
            last_radius = dist_to_home
    return alarm, alarm_time, min_radius, packet_time


def print_planes(plane_history, hexes):
    """
    Print the planes. Returns the number of lines printed.
    :param plane_history: the data for the planes
    :param hexes: The list of plane hexes
    :return: The number of lines printed
    """

    def get_distance(d):
        """
        Get the distance from a plane dictionary (used for sorting)
        :param d:  The dictionary representing the plane
        :return: the latest distance
        """
        try:
            return d['distance_history'][-1][0]
        except IndexError:
            return 10000

    def is_not_empty(d):  # TODO: Plane?
        """
        Check if there is any data in plane dictionary
        :param d: The plane dictionary
        :return: True or False
        """
        for key in d.keys():
            if len(d[key]):
                return True
        return False

    last_printed = 0
    sorted_dist = sorted(plane_history.values(), key=get_distance)
    for data_plane in sorted_dist:
        try:
            hex_code = list(plane_history.keys())[list(plane_history.values()).index(data_plane)]
            if (aircraft_json['aircraft'][hexes[hex_code]]['seen'] < CONFIG['remember']) and is_not_empty(data_plane):
                print_the_plane(data_plane, hex_code)
                last_printed += 1
        except KeyError:  # aircraft no longer exists
            continue
    return last_printed


def get_current_lat_long(plane_data):
    """
    Obtain the three lat/long pairs we use from a plane.
    :param plane_data: A dictionary representing a plane.
    :return: The lat/long pairs, and the index of the variable lat/long pair (oldest)
    """
    current = plane_data['lat_history'][-1][0], plane_data['lon_history'][-1][0]
    last = plane_data['lat_history'][-2][0], plane_data['lon_history'][-2][0]
    if min(len(plane_data['lat_history']), len(plane_data['lon_history'])) < CONFIG['lat_lon_packet_age_max']:
        # If we have too few packets to average out, use the oldest one
        old_index = 0  # packet id
        oldest = plane_data['lat_history'][0][0], plane_data['lon_history'][0][0]

    else:
        # Go back to the oldest packet that's relevant as set by CONFIG['lat_lon_packet_age_max']
        oldest = plane_data['lat_history'][-1 * CONFIG['lat_lon_packet_age_max']][0], \
            plane_data['lon_history'][-1 * CONFIG['lat_lon_packet_age_max']][0]
        old_index = -1 * CONFIG['lat_lon_packet_age_max']
    return current, last, oldest, old_index


def calculate_heading_speed_alarm(plane_data):
    """
    Calculate the heading, speed, whether we should raise an alarm, and how long we have and update it
    :param plane_data: The plane data for one plane
    :return: Nothing
    """
    current_lat_long, last_lat_long, oldest_lat_long, old_index = get_current_lat_long(plane_data)
    # Distance between the oldest relevant value and current position
    dist_xz = geopy.distance.geodesic(current_lat_long, oldest_lat_long).m
    # Time between these values
    time_between = plane_data['lat_history'][-1][1] - plane_data['lat_history'][old_index][1]
    # Heading
    heading_xz = calculate_heading_directions(last_lat_long, current_lat_long)
    # Calculated time/value pair
    ncalc_heading = [heading_xz, plane_data['lat_history'][-1][1]]
    patch_add(plane_data, 'calc_heading_history', ncalc_heading)
    ncalc_speed = [dist_xz / time_between * 3.6, plane_data['lat_history'][-1][1]]  # same as heading
    patch_add(plane_data, 'calc_speed_history', ncalc_speed)
    alarm, alarm_time, min_radius, packet_time = get_alarm_info(current_lat_long, last_lat_long, time_between,
                                                                plane_data)
    date_old = current_time_aircraft - packet_time
    plane_data['alarm_history'].append([alarm, current_time_aircraft])
    if alarm_time == -1:
        inp = 'NO'
    else:
        inp = alarm_time - date_old
    plane_data['time_until_entry_history'].append([inp, current_time_aircraft])


def calculate_distance(plane_data):
    """
    Calculate and update the distance for the plane represented by plane_data
    :param plane_data: The plane data for one plane
    :return: none
    """
    current_lat_long = plane_data['lat_history'][-1][0], plane_data['lon_history'][-1][0]
    packet_time = max(plane_data['lat_history'][-1][1], plane_data['lon_history'][-1][1])
    ndistance = [geopy.distance.geodesic(HOME, current_lat_long).km, packet_time]
    patch_add(plane_data, 'distance_history', ndistance)


def print_heading():
    """
    Print the heading
    :return: none
    """
    if not args.quiet:
        print(" " * 8, end='')
        for item in ['flight', 'lat', 'lon', 'nav_heading', 'alt_baro',
                     'calc_heading', 'calc_speed', 'alarm', 'time_until_entry', 'distance']:
            print(item + " " * 10, end='')
        print()
    else:
        print("Started.")

def print_quiet():
    delete_last_line()
    if CONFIG['run_for'] == -1:
        print("Running indefinitely. On tick", tick)
    else:
        print(str(tick + 1) + "/" + str(CONFIG['run_for']))
def collect_data(aircraft_json, plane_history):
    """
    Collect and calculate data for each aircraft and store in plane_history
    :param aircraft_json: The aircraft data (raw)
    :param plane_history: Our processed data object to dump to
    :return: nothing
    """
    for aircraft in aircraft_json['aircraft']:
        if aircraft['seen'] > CONFIG['remember']:  # don't even bother
            continue
        if aircraft['hex'] not in plane_history.keys():  # If we haven't seen this plane before, create a new one
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
        plane_data = plane_history[aircraft['hex']]  # A reference to plane (TODO: Plane)
        if not len(plane_data['flight_name_id']):  # If we don't have a flight id stored
            if 'flight' in aircraft.keys():  # If there is an available flight id, add it!
                plane_data['flight_name_id'] = [0, [aircraft['flight']]]  # So this plays nice with print_the_plane
        for item in ['lat', 'lon', 'nav_heading', 'alt_baro']:  # Stats in aircraft_json that are retrievable
            if item in aircraft.keys():
                if not (len(plane_data[item + '_history']) and plane_data[item + '_history'][-1][0] == aircraft[item]):
                    plane_data[item + '_history'].append((float(aircraft[item]), current_time_aircraft))
        if min([len(plane_data['lat_history']), len(plane_data['lon_history'])]) >= 2:  # If we have at least two
            # values for the lat/long for this plane, we can calculate heading, speed, alarm, and time_until_entry
            calculate_heading_speed_alarm(plane_data)
        if min([len(plane_data['lat_history']), len(plane_data['lon_history'])]) >= 1:  # If we have a full lat/long
            # pair, then calculate the distance using geodesic
            calculate_distance(plane_data)
    return {i[1]: i[0] for i in [(ind, i['hex']) for ind, i in enumerate(aircraft_json['aircraft'])]}


def dump_json(cwd):
    if os.path.exists(cwd+"/dump.json"):
        os.remove(cwd+"/dump.json")
    json.dump(plane_history, open(cwd+'/dump.json', 'x'), indent=4, sort_keys=True)


if __name__ == '__main__':
    start()
    start_directory = os.getcwd()
    plane_history = {}
    aircraft_json = json.load(open(CONFIG['dump1090_dir'] + '/airstrik_data/aircraft.json'))
    current_time_aircraft = 0  # start the time at 0 to ensure that load_aircraft_json waits for a new packet,
    # instead of accepting a non-existent packet
    last_printed = 1
    print_heading()
    print()
    tick = 0
    while tick != CONFIG['run_for']:
        aircraft_json, new_aircraft_time = load_aircraft_json(current_time_aircraft)
        current_time_aircraft = new_aircraft_time
        hexes = collect_data(aircraft_json, plane_history)
        if args.quiet:
            print_quiet()
        else:
            delete_last_line(lines=last_printed)  # delete lines from stdout
            last_printed = print_planes(plane_history, hexes)
        tick += 1
    if not args.no_dump:
        dump_json(start_directory)
