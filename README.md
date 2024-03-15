*Update: [PyAerial](https://github.com/quantumbagel/PyAerial) is now under development and will replace airstrik.py when ready. More information on my [website](https://quantumbagel.github.io/PyAerial).*

# airstrik.py

A ~~overly complicated~~ simple program to track planes via ADS-B and alert you if the plane enters a predefined area, store the data in MongoDB, and even send alerts to a Kakfa server.


### Feature list
* Uses MongoDB to store plane data
* Very space-efficient, only storing the data from the plane's closest location.
* Can run inside Docker Compose
* Customizable filters
* Can predict when a airplane will enter the zone set using trigonometry 
### Setup

Run `git clone https://github.com/quantumbagel/airstrik.py.git`

Change the values in `config.yaml` to what you want (I would recommend just changing the lat/long to your current location to test)

Here's a quick description of the values in `config.yaml`:

| Item                   | Description                                                                                                                                                                                        |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| think_ahead            | How much time (in seconds) to simulate the aircraft's position ahead of where it is for the early warning system. (default=120)                                                                    |
| lat_lon_packet_age_max | To prevent erratic values, airstrik uses an average from an older lat/long packet and current one. This is the maximum packet age. (default=10)                                                    |
| home                   | This stores your current lat/long to calculate various things. !!!This must be extremely accurate!!! (default=35.77031, -78.68078)                                                                 |              
| remember               | The maximum amount of time in seconds that an aircraft is kept around before deleting from RAM and saving to mongodb (default=45)                                                                  |
| decimation_factor      | This is, essentially, how much data to store to the database. If this is 0, only the closest will be stored, but otherwise every nth unique set of information will be stored to the db.           |
| dump1090_dir           | This should be kept at its current value if you use the installer. If you do not, set this to the directory of Flightaware's dump1090  (or Mutability's dump978)                                   |
| json_speed             | How much time (seconds) that dump1090 waits before getting updates. (default=0)                                                                                                                    |
| min_trip_length        | The minimum amount of time (seconds) we must receive packets from an aircraft for us to save it to mongodb. (we don't want a plane sending us one packet to be saved to the database) (default=90) |
| print_top_planes       | Print only this number of the closest planes. -1 is all planes. (default=-1) (DEPRECATED)                                                                                                          |
| mongo_address          | The address of the MongoDB database to connect to                                                                                                                                                  |
| filters                | Write filters as a key-value in this format: <name>: [max <distance(km)>, max <alt(m)>]                                                                                                            |
| kafka_address          | The address of the Kafka server to send events to. Leave this empty to print events to console.                                                                                                    |
Here's a list of the command line arguments to `airstrik.py`:

| Item                      | Description                                                                                                                          |
|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| -q (--quiet)              | Set the output mode to quiet, which turns off all non-error output                                                                   |
| -c (--config) <FILE>      | Set the directory or relative path to the configuration file (default config.yaml)                                                   |
| -d (--device) <DEVICE>    | Set the RTLSDR device index or serial number to use if you have multiple receivers. Default is index 0                               |
| --database-out <DATABASE> | Set the MongoDB database to dump data to (default airstrikdb)                                                                        |
| --no-purge                | Don't purge old data folders on startup. This is useful when you have multiple receivers and don't want to crash the other instance. |
| --log-mode                | Print in a log mode instead of a auto-refreshing mode. This argument overrides -q/--quiet.                                           |
| --no-start-dump           | Don't start dump1090/dump978 and provide the directory where the data is.                                                            |
| --run-dump-978            | Run dump978 instead of dump1090. This should be only used for receivers that are 978mhz.                                             |


### Kafka

The Kafka implementation is designed to help alert other programs, such as drone flight managers, when the airplanes have entered an area where they may become or are a problem.
If the `kafka_address` argument is set in `config.yaml`, the program will update two topics to that Kafka server: `airstrik-alert` and `airstrik-warning`. 
`airstrik-alert` is only triggered when the plane is inside the widest filter, but the `airstrik-warning` is sent when the plane is within `think_ahead` seconds of entering the zone.
Here are the paramaters sent.

| Key        | Value                                                                                                                                  |
|------------|----------------------------------------------------------------------------------------------------------------------------------------|
| plane_hex  | The hex address of the plane.                                                                                                          |
| plane_id   | The flight identification tag of the plane. This will be an empty string if the airplane has not sent its tag.                         |
| plane_time | The epoch time on the plane packet. This should be the current epoch time, but if differs can be used to calculate the ETA epoch time. |
| heading    | The heading of the plane.                                                                                                              |
| speed      | The speed (km/h) that the plane is going.                                                                                              |
| altitude   | The altitude (m) from sea level of the plane.                                                                                          |
| latitude   | The latitude of the plane.                                                                                                             |                        
| longitude  | The longitude of the plane.                                                                                                            |
| distance   | The distance of the plane from set origin point (m)                                                                                    |
| eta        | How many seconds until the plane enters the widest filter. (airstrik-warning only)                                                     |






### Installation
There are two ways to install airstrik.py, Docker Compose and systemd. Docker Compose is recommended due to the ease of setup and independence from the rest of the system, although both work fine.

## systemd

Edit `airstrikd.service`'s `ExecStart` and `WorkingDirectory` parameters to the location of airstrik_mongo.py and 
where you git cloned to.

Also set your python version in the `ExecStart` parameter (I use /usr/bin/python3.10, but just run `which python3`) to find out where python is installed. If you have multiple `python3`'s and aren't using the one your system aliases to `python3`, then change the python name in `install.sh` (line 12) from `python3` to `python3.12` or whatever.

Run `./install.sh` to install.

When this is done, confirm that 

1. mongod.service exists (`systemctl status mongod`)
2. airstrikd.service exists (`systemctl status airstrikd`)
3. dump1090 works (`cd` into its directory (the subfolder `dump1090`) and run (with the antenna plugged in) `./dump1090 --interactive`). If you see planes showing up, you are good to go!


Now, run `systemctl enable airstrikd && systemctl start airstrikd` to start up!


## Docker Compose

Run `sudo docker compose build && sudo docker compose up -d` to install and run.


If the service or container crashed, post an issue with the output of `journalctl -e -u airstrikd` and I'll try to help.
