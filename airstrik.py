import datetime
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

import pymongo.errors
import ruamel.yaml
from pymongo.mongo_client import MongoClient
from kafka import KafkaProducer

parser = argparse.ArgumentParser(prog='airstrik.py', description='A simple program to track and detect airplanes '
                                                                 'heading towards the AERPAW field.', epilog='Go Pack!')
parser.add_argument('-q', '--quiet', action='store_true')
parser.add_argument('-c', '--config', default='config.yaml', help='The config file\'s location (yaml). ')
parser.add_argument('-d', '--device', default="0", type=str, help='The index/serial of the RTLSDR device')
parser.add_argument('--database-out', default='airstrikdb', help='The mongo database to write to')
parser.add_argument('--no-purge', action='store_true', help="Don't purge other running instances")
parser.add_argument('--log-mode', action='store_true', help='use this if running headless')
# ADD FLAG for --run-978
parser.add_argument('--no-start-dump', default='', help='provide the dump subdirectory where the data is')
parser.add_argument('--run-dump-978', action='store_true', help='run dump 978?')
args = parser.parse_args()
config_file = ruamel.yaml.YAML()
CONFIG = config_file.load(open(args.config))
time_start = str(time.time())
end_process = False
is_relative_dir = CONFIG['dump1090_dir'].startswith('.')
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


def is_not_empty(d):
    """
    Check if there is any data in plane dictionary
    :param d: The plane dictionary
    :return: True or False
    """
    for key in d.keys():
        if key != 'start_time' and len(d[key]):
            return True
    return False


def run_dump978():
    """
    Run dump978 as a daemon subprocess
    :return: None
    """
    global end_process
    os.chdir(CONFIG['dump1090_dir'])
    p = subprocess.Popen("sudo rtl_sdr -d" + args.device +
                         " -f 978000000 -s 2083334 -g 49.6 - | ./dump978 | ./uat2json airstrikdata", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    atexit.register(p.terminate)
    stdout, stderr = p.communicate()
    if p.returncode:
        print(stderr)
        end_process = True


def run_dump1090():
    """
    Run dump1090 as a daemon subprocess
    :return: None
    """
    global end_process
    os.chdir(CONFIG['dump1090_dir'])
    p = subprocess.Popen("sudo ./dump1090 --quiet --write-json airstrik_data" + time_start +
                         " --write-json-every " + str(CONFIG['json_speed']) + " --device " + str(args.device),
                         shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    atexit.register(p.terminate)
    stdout, stderr = p.communicate()
    if p.returncode:
        print(stderr)
        end_process = True


def start():
    """
    A function to remove the output directory and recreate it, and wait for dump1090 to start
    :return: none
    """
    global end_process
    if not args.no_start_dump:
        if not args.no_purge:
            subprocess.run("rm -rf " + CONFIG['dump1090_dir'] + "/airstrik_data*", shell=True)
        mkc = "mkdir -m 777 " + CONFIG['dump1090_dir'] + "/airstrik_data" + time_start
        subprocess.run(mkc, shell=True)
        if not args.run_dump_978:
            t = threading.Thread(target=run_dump1090, daemon=True)
        else:
            t = threading.Thread(target=run_dump978, daemon=True)
        t.start()
    print("Loading...", end='')
    sys.stdout.flush()
    if args.no_start_dump:
        airstrikdir = CONFIG['dump1090_dir'] + '/' + args.no_start_dump
    else:
        airstrikdir = CONFIG['dump1090_dir'] + '/airstrik_data' + time_start + '/'
    if args.run_dump_978:
        airstrikdir = CONFIG['dump1090_dir'] + '/airstrikdata'
    while 'aircraft.json' not in os.listdir(airstrikdir):
        if end_process:
            print("Failed! (antenna not plugged in?)")
            sys.exit(1)
        print(".", end='')
        sys.stdout.flush()
        time.sleep(0.1)
    print()


def print_the_plane(plane, hex_value):  # move to Plane?
    """
    Print one plane's datd
    :param plane: The plane's data
    :param hex_value: The hex value of the aircraft
    :return: nothing
    """
    print(hex_value + ": ", end='')
    for item in plane:
        if item == 'extras':
            continue
        try:
            print(str(plane[item][-1][0]) + (len(item) - len(str(plane[item][-1][0])) + 1) * ' ', end=' ')
        except Exception:
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
    heading_rads = ((heading_rads * 180 / math.pi) + 360) % 360
    return heading_rads


def print_log_mode():
    """
    A function to print a log (systemd mode/docker mode)
    :return: none
    """
    print("We have seen", total_uploads, 'plane trips.')
    plns = 0
    for data_plane in plane_history.values():
        try:
            hex_code = list(plane_history.keys())[list(plane_history.values()).index(data_plane)]
            if (aircraft_json['aircraft'][hexes[hex_code]]['seen'] < CONFIG['remember']) and is_not_empty(data_plane):
                plns += 1
        except KeyError:  # aircraft no longer exists
            continue
        except ValueError:
            continue
    print("We are currently observing", plns, 'planes')
    print("Current alarm plane stats (trip, planes, alarmtrip, alarmplane)",
          current_day_trip[0], len(current_day_planes), current_day_alarm_trip[0], len(current_day_alarm_planes))


def load_aircraft_json(current_time_aircraft):
    """
    A function to wait for json updates, and return them
    :param current_time_aircraft: The current aircraft time
    :return: The new json, and new time
    """
    while True:
        if end_process:
            print("Failed! (likely antenna is unplugged)")
            sys.exit(1)
        if args.run_dump_978:
            a_json = json.load(open(CONFIG['dump1090_dir'] + '/airstrikdata/aircraft.json'))
        elif args.no_start_dump:
            a_json = json.load(open(CONFIG['dump1090_dir'] + '/' + args.no_start_dump + '/aircraft.json'))
        else:
            a_json = json.load(open(CONFIG['dump1090_dir'] + '/airstrik_data' + time_start + '/aircraft.json'))
        new_current_time_aircraft = float(a_json['now'])
        if new_current_time_aircraft != current_time_aircraft:
            break
    return a_json, new_current_time_aircraft


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


def get_alarm_info(hex, current_lat_long, plane_data):
    """
    Calculate the alarm information by simulating the plane given in plane_data
    :param current_lat_long: The current lat/long of the plane
    :param plane_data: the data for the plane
    :return: whether the alarm should be raised, the time we have, and how close to the center it will get,
     as well as when this was updated
    """

    min_radius = 100000000
    packet_time = max(plane_data['lat_history'][-1][1], plane_data['lon_history'][-1][1])
    alarm_time = -1
    alarm_ll = False
    last_radius = 100000000
    did_raise_alarm = False
    matched_filters = match_filters(plane_data['distance_history'][-1][0])
    if len(matched_filters.keys()):  # if we are in the zone, don't bother
        raise_alarm(hex, plane_data, 0)
        did_raise_alarm = True
    for second in range(CONFIG['think_ahead']):
        if len(plane_data['calc_heading_history']):
            destination = (
                geopy.distance.geodesic(kilometers=second * plane_data['calc_speed_history'][-1][0] * 1 / 3600)
                .destination(current_lat_long, plane_data['calc_heading_history'][-1][0]))
            new_lat, new_long = destination.latitude, destination.longitude
        elif len(plane_data['nav_heading_history']):
            destination = (
                geopy.distance.geodesic(kilometers=second * plane_data['calc_speed_history'][-1][0] * 1 / 3600)
                .destination(current_lat_long, plane_data['nav_heading_history'][-1][0]))
            new_lat, new_long = destination.latitude, destination.longitude
        else:
            return False, -1, 0, 0
        if new_lat > 90 or new_lat < -90 or new_long > 90 or new_long < -90:
            break
        new_coords = (new_lat, new_long)
        dist_to_home = geopy.distance.geodesic(new_coords, HOME).km
        alarm_lat_long = dist_to_home < most_generous_dist
        if alarm_lat_long:
            alarm_ll = True
            if alarm_time == -1:
                alarm_time = second
            if dist_to_home < min_radius:
                min_radius = dist_to_home
            if dist_to_home > last_radius:
                break
            last_radius = dist_to_home
    if not did_raise_alarm:
        if -1 < alarm_time < CONFIG['think_ahead']:
            raise_alarm(hex, plane_data, alarm_time)
    if len(plane_data['alt_geom_history']):
        alarm = alarm_ll and plane_data['alt_geom_history'][-1][0] <= most_generous_alt
    else:
        alarm = alarm_ll
    if alarm and (plane_data['distance_history'][-1][0] < most_generous_dist):
        plane_data['extras']['alarm_triggered'] = True
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

    lp = 2
    plns = 0
    sorted_dist = sorted(plane_history.values(), key=get_distance)
    for data_plane in sorted_dist:
        try:
            hex_code = list(plane_history.keys())[list(plane_history.values()).index(data_plane)]
            if (aircraft_json['aircraft'][hexes[hex_code]]['seen'] < CONFIG['remember']) and is_not_empty(data_plane):
                plns += 1
                if not (plns >= CONFIG['print_top_planes']):
                    print_the_plane(data_plane, hex_code)
                    lp += 1
        except KeyError:  # aircraft no longer exists
            continue
    print("We have seen", total_uploads, 'plane trips.')
    print("Currently parsing", plns, "planes.")
    return lp


def raise_alarm(hx, plane_data, eta):
    """
    Raise the alarm!
    :param hx: the hex of the plane
    :param plane_data: The data of the plane triggering the alarm
    :param eta: the ETA of the plane
    :return: nothing
    """
    if not len(plane_data['alt_geom_history']):
        alt_geom = 'unknown'
    else:
        alt_geom = plane_data['alt_geom_history'][-1][0]
    if not len(plane_data['flight_name_id']):
        flight_id = ''
    else:
        flight_id = plane_data['flight_name_id'][0][0]
    if eta > 0:
        to_send = {'plane_hex': hx,
                   'plane_id': flight_id,
                   "plane_time": datetime.datetime.fromtimestamp(current_time_aircraft),
                   "heading": plane_data['calc_heading_history'][-1][0],
                   "speed": plane_data['calc_speed_history'][-1][0],
                   "altitude": alt_geom,
                   "latitude": plane_data['lat_history'][-1][0],
                   'longitude': plane_data['lon_history'][-1][0],
                   "distance": plane_data['distance_history'][-1][0],
                   'eta': eta}
        if CONFIG['kafka_address']:
            producer.send('airstrik-warning', to_send)
        else:
            print("airstrik-warning: ", end='')
            for item in to_send.keys():
                print(f"{item}: {to_send[item]}, ", end='')
            print()
    else:
        to_send = {'plane_hex': hx,
                   'plane_id': flight_id,
                   "plane_time": datetime.datetime.fromtimestamp(current_time_aircraft),
                   "heading": plane_data['calc_heading_history'][-1][0],
                   "speed": plane_data['calc_speed_history'][-1][0],
                   "altitude": alt_geom,
                   "latitude": plane_data['lat_history'][-1][0],
                   'longitude': plane_data['lon_history'][-1][0],
                   "distance": plane_data['distance_history'][-1][0]}
        if CONFIG['kafka_address']:
            producer.send("airstrik-alert", to_send)
        else:
            print("airstrik-alert: ", end='')
            for item in to_send.keys():
                print(f"{item}: {to_send[item]}, ", end='')
            print()


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


def calculate_heading_speed_alarm(plane_data, hx):
    """
    Calculate the heading, speed, whether we should raise an alarm, and how long we have and update it
    :param plane_data: The plane data for one plane
    :return: Nothing
    """
    current_lat_long, last_lat_long, oldest_lat_long, old_index = get_current_lat_long(plane_data)
    # Distance between the oldest relevant value and current position
    dist_xz = geopy.distance.geodesic(current_lat_long, oldest_lat_long).m
    # Time between these values
    time_between = plane_data['lat_history'][-1][1] - plane_data['lat_history'][old_index][1]  # replace with old_index
    # Heading
    heading_xz = calculate_heading_directions(last_lat_long, current_lat_long)
    # Calculated time/value pair
    ncalc_heading = [heading_xz, plane_data['lat_history'][-1][1]]
    patch_add(plane_data, 'calc_heading_history', ncalc_heading)
    ncalc_speed = [round(dist_xz / time_between * 3.6, 4), plane_data['lat_history'][-1][1]]  # same as heading
    patch_add(plane_data, 'calc_speed_history', ncalc_speed)
    alarm, alarm_time, min_radius, packet_time = get_alarm_info(hx, current_lat_long, plane_data)
    if len(plane_data['alarm_history']) == 0 or plane_data['alarm_history'][-1][0] != alarm:
        plane_data['alarm_history'].append([alarm, current_time_aircraft])


def match_filters(closest_dist, closest_alt=None):
    all_filters = CONFIG['filters']
    filter_structure = {}
    for each_filter in all_filters.keys():
        distance = all_filters[each_filter][0]
        altitude = all_filters[each_filter][1]
        if closest_alt is None:
            alt_check = True
        else:
            alt_check = closest_alt <= altitude
        if closest_dist <= distance and alt_check:
            filter_structure.update({each_filter: {'dist': distance, 'alt': altitude}})
    return filter_structure


def calculate_distance(plane_data):
    """
    Calculate and update the distance for the plane represented by plane_data
    :param plane_data: The plane data for one plane
    :return: none
    """
    current_lat_long = plane_data['lat_history'][-1][0], plane_data['lon_history'][-1][0]
    packet_time = max(plane_data['lat_history'][-1][1], plane_data['lon_history'][-1][1])
    ndistance = [round(geopy.distance.geodesic(HOME, current_lat_long).km, 4), packet_time]
    patch_add(plane_data, 'distance_history', ndistance)


def print_heading():
    """
    Print the heading
    :return: none
    """
    if not args.quiet:
        print(" " * 8, end='')
        for item in ['flight', 'lat', 'lon', 'nav_heading', 'alt_geom',
                     'calc_heading', 'calc_speed', 'alarm', 'distance']:
            print(item + " " * 10, end='')
        print()
    else:
        print("Started.")


def print_quiet():
    delete_last_line(lines=3)
    plns = 0
    for data_plane in plane_history:
        try:
            hex_code = list(plane_history.keys())[list(plane_history.values()).index(data_plane)]
            if (aircraft_json['aircraft'][hexes[hex_code]]['seen'] < CONFIG['remember']) and is_not_empty(data_plane):
                plns += 1
        except KeyError:  # aircraft no longer exists
            continue
        except ValueError:
            continue
    print("We have seen", total_uploads, 'plane trips.')
    print("Currently parsing", plns, "planes.")


def collect_data(a_json, plane_history):
    """
    Collect and calculate data for each aircraft and store in plane_history
    :param a_json: The aircraft data (raw)
    :param plane_history: Our processed data object to dump to
    :return: nothing
    """
    global total_uploads
    for aircraft in a_json['aircraft']:
        if aircraft['seen'] > CONFIG['remember']:  # don't even bother / try to upload?
            try:
                ac_dt = plane_history[aircraft['hex']]
            except KeyError:
                continue
            if (a_json['now'] - aircraft['seen']) - \
                    plane_history[aircraft['hex']]['extras']['start_time'] < CONFIG['min_trip_length']:
                del plane_history[aircraft['hex']]
                continue
            if plane_history[aircraft['hex']]['extras']['alarm_triggered']:
                closest_time = 0
                closest_dist = 10000000
                for dst in plane_history[aircraft['hex']]['distance_history']:
                    if dst[0] < closest_dist:
                        closest_time = dst[1]
                        closest_dist = dst[0]
                write = {}
                for item in plane_history[aircraft['hex']].keys():
                    if item in ['extras', 'alarm_history', 'flight_id']:
                        continue
                    if item in ['nav_heading_history', 'alt_geom_history'] and args.run_dump_978:  # not supported:
                        continue
                    dw = False
                    for kval in plane_history[aircraft['hex']][item][::-1]:
                        if kval[1] <= closest_time:
                            write.update({item.replace('_history', ''): kval})
                            dw = True
                    if not dw:
                        if item == 'flight_name_id':
                            try:
                                flight_predictor_json = json.load(open(start_directory + '/icao.json'))
                                flight_name = flight_predictor_json[aircraft['hex']]
                                del flight_predictor_json
                                write.update({'flight_name_id': [flight_name + ' (p)', a_json['now']]})
                                continue
                            except KeyError:
                                write.update({'flight_name_id': None})
                                continue
                        else:
                            write.update({item.replace('_history', ''): None})
                write['extras'] = {'start_time': ac_dt['extras']['start_time']}
                write['extras'].update({"end_time": a_json['now']})
                if not args.run_dump_978 and (write['alt_geom'] is not None):
                    matched_filters = match_filters(write['distance'][0], write['alt_geom'][0])
                    if not len(matched_filters):
                        del plane_history[aircraft['hex']]
                        continue
                    write['filters'] = matched_filters
                else:
                    matched_filters = match_filters(write['distance'][0])
                    if not len(matched_filters):
                        del plane_history[aircraft['hex']]
                        continue
                    write['filters'] = matched_filters
                if aircraft['hex'] not in current_day_planes:
                    current_day_planes.append(aircraft['hex'])
                if aircraft['hex'] not in current_day_alarm_planes:
                    current_day_alarm_planes.append(aircraft['hex'])
                current_day_alarm_trip[0] += 1
                current_day_trip[0] += 1
                write['flight_id'] = aircraft['hex']
                database["flight_records"].insert_one(write)
            else:
                if aircraft['hex'] not in current_day_planes:
                    current_day_planes.append(aircraft['hex'])
                current_day_trip[0] += 1
            del plane_history[aircraft['hex']]
            total_uploads += 1
            continue
        if (aircraft['hex'] not in plane_history.keys()) and (aircraft['seen'] < CONFIG['remember']):
            # If we haven't seen this plane before, create a new one
            plane_history.update({aircraft['hex']: {"flight_name_id": [],
                                                    "flight_id": aircraft['hex'],
                                                    "extras": {"start_time": a_json['now'],
                                                               'alarm_triggered': False,
                                                               'end_time': None,
                                                               'decimation_tracker': 0,
                                                               'last_written': {}},
                                                    "lat_history": [],
                                                    "lon_history": [],
                                                    "nav_heading_history": [],
                                                    "alt_geom_history": [],
                                                    "calc_heading_history": [],
                                                    "calc_speed_history": [],
                                                    'alarm_history': [],
                                                    'distance_history': [],
                                                    'filters': []}})
        plane_data = plane_history[aircraft['hex']]  # A reference to plane
        if not len(plane_data['flight_name_id']):  # If we don't have a flight id stored
            if 'flight' in aircraft.keys():  # If there is an available flight id, add it!
                plane_data['flight_name_id'] = [[str(aircraft['flight']).replace(' ', ''), a_json['now']]]
                # So this plays nice with print_the_plane
        for item in ['lat', 'lon', 'nav_heading', 'alt_geom']:  # Stats in a_json that are retrievable
            if item in aircraft.keys():
                if not (len(plane_data[item + '_history']) and plane_data[item + '_history'][-1][0] == aircraft[item]):
                    plane_data[item + '_history'].append((float(aircraft[item]), current_time_aircraft))
        if min([len(plane_data['lat_history']), len(plane_data['lon_history'])]) >= 2:  # If we have at least two
            # values for the lat/long for this plane, we can calculate heading, speed, alarm, and time_until_entry
            calculate_heading_speed_alarm(plane_data, aircraft['hex'])
        if min([len(plane_data['lat_history']), len(plane_data['lon_history'])]) >= 1:  # If we have a full lat/long
            # pair, then calculate the distance using geodesic
            calculate_distance(plane_data)
        if (plane_data['extras']['decimation_tracker'] <= 0 and CONFIG['decimation_factor'] != 0
                and len(plane_data['lat_history']) > 1):  # add to mongodb
            # if we have a new lat/long, which updates everything relevant
            if len(plane_data['nav_heading_history']):
                nav_h = plane_data['nav_heading_history'][-1]
            else:
                nav_h = None
            if len(plane_data['alt_geom_history']):
                alt_g = plane_data['alt_geom_history'][-1]
            else:
                alt_g = None
            if not len(plane_data['calc_heading_history']):
                print("For some reason, there are two lat/longs, but no calc heading lol")
                print(f"Lat longs: {plane_data['lat_history']}, calc heading {plane_data['calc_heading_history']}")
                plane_data['extras']['decimation_tracker'] = CONFIG['decimation_factor'] - 1  # until a fix is found
                # just reset lol
                continue
            write = {'flight_name_id': plane_data['flight_name_id'],
                     'lat': plane_data['lat_history'][-1],
                     'lon': plane_data['lon_history'][-1],
                     'nav_heading': nav_h,
                     'alt_geom': alt_g,
                     'calc_heading': plane_data['calc_heading_history'][-1],
                     'calc_speed': plane_data['calc_speed_history'][-1],
                     'distance': plane_data['distance_history'][-1],
                     'extras': {'start_time': plane_data['extras']['start_time']},
                     'filters': plane_data['filters'],
                     'flight_id': plane_data['flight_id']}
            if not CONFIG['decimation_force_new_data'] and len(plane_data['extras']['last_written'].keys()) == 0:
                # if we don't have to have new data, just write the data in
                database['flight_records'].insert_one(write)
                print("written (force new data)")
                plane_data['extras']['decimation_tracker'] = CONFIG['decimation_factor'] - 1
            # otherwise, check for new data
            elif len(plane_data['extras']['last_written'].keys()) != 0 and \
                    (plane_data['extras']['last_written']['lat'] != plane_data['lat_history'][-1][0] or
                     plane_data['extras']['last_written']['lon'] != plane_data['lon_history'][-1][0]):
                print("written (if new data)")
                database['flight_records'].insert_one(write)
                plane_data['extras']['decimation_tracker'] = CONFIG['decimation_factor'] - 1
            plane_data['extras']['last_written'] = {'lat': write['lat'], 'lon': write['lon']} # update LastWritten
        else:
            plane_data['extras']['decimation_tracker'] -= 1
    return {i[1]: i[0] for i in [(ind, i['hex']) for ind, i in enumerate(a_json['aircraft'])]}


if __name__ == '__main__':
    start_directory = os.getcwd()
    # Get the original starting directory so entering dump1090/dump978's directory works ok and doesn't break
    if is_relative_dir:  # relative directory detection
        CONFIG['dump1090_dir'] = start_directory + CONFIG['dump1090_dir'][1:]
    start()
    plane_history = {}
    if args.run_dump_978:
        aircraft_json = json.load(open(CONFIG['dump1090_dir'] + '/airstrikdata/aircraft.json'))
        f = open('airstrikdata/receiver.json', 'w')
        json.dump({"version": "dump978-uat2json", "refresh": 0, "history": 0}, f)
    elif args.no_start_dump:
        aircraft_json = json.load(open(CONFIG['dump1090_dir'] + '/' + args.no_start_dump + '/aircraft.json'))
    else:
        aircraft_json = json.load(open(CONFIG['dump1090_dir'] + '/airstrik_data' + time_start + '/aircraft.json'))

    current_time_aircraft = 0  # start the time at 0 to ensure that load_aircraft_json waits for a new packet,
    # instead of accepting a non-existent packet
    last_printed = 1
    client = MongoClient(CONFIG['mongo_address'])
    database = client[args.database_out]
    if not (args.quiet or args.log_mode):
        print_heading()
    total_uploads = 0
    if CONFIG['kafka_address']:
        producer = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                                 bootstrap_servers=[CONFIG['kafka_address']])
    print()  # add an extra buffer line
    # We need to store the trip count in a list to ensure that it can be accessed globally due to python shenanigans
    current_day_trip = [0]
    current_day_planes = []
    current_day_alarm_trip = [0]
    current_day_alarm_planes = []
    tz = datetime.timezone(datetime.timedelta(hours=CONFIG['utc_time_offset']))
    current_day = datetime.datetime.now(tz=tz).day  # set up the day tracking
    most_generous_alt = max([i[1] for i in CONFIG['filters'].values()])  # find the biggest filter values
    most_generous_dist = max([i[0] for i in CONFIG['filters'].values()])
    while True:
        if current_day != datetime.datetime.now(tz=tz).day:  # the day changed! store stats
            try:
                database['stats'].insert_one(
                    {"_id": str(datetime.datetime.now(tz=tz).date() - datetime.timedelta(days=1)),
                     # we use yesterday because it's tomorrow
                     "unique_planes": len(current_day_planes),
                     'total_trips': current_day_trip[0],
                     'unique_alarm_planes': len(current_day_alarm_planes),
                     'total_alarm_trips': current_day_alarm_trip[0]})
            except pymongo.errors.DuplicateKeyError:
                print("Failed to write stats information because of a DuplicateKeyError!"
                      " Going to overwrite the stat data instead.")
                for collection in database['stats']:
                    if collection['_id'] == str(datetime.datetime.now(tz=tz).date() - datetime.timedelta(days=1)):
                        collection['unique_planes'] = len(current_day_planes)
                        collection['total_trips'] = current_day_trip[0]
                        collection['unique_alarm_planes'] = len(current_day_alarm_planes)
                        collection['total_alarm_trips'] = current_day_alarm_trip[0]

            current_day_trip = [0]  # reset counters
            current_day_planes = []
            current_day_alarm_trip = [0]
            current_day_alarm_planes = []
            current_day = datetime.datetime.now().day
        if end_process:  # The dump1090/dump978 has crashed!
            print("Failed! (antenna gone?)")
            sys.exit(1)
        aircraft_json, new_aircraft_time = load_aircraft_json(current_time_aircraft)  # Update json
        current_time_aircraft = new_aircraft_time  # Sync aircraft time
        hexes = collect_data(aircraft_json, plane_history)  # Update data
        if args.log_mode:  # Use log mode?
            print_log_mode()
            continue
        if args.quiet:  # Use quiet mode?
            print_quiet()
        else:  # Use default mode.
            delete_last_line(lines=last_printed)  # delete lines from stdout
            last_printed = print_planes(plane_history, hexes)
