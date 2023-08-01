# Installation Guide

<p>Here's a guide to installing airstrik.py.</p>

### Setup

Run `git clone https://github.com/quantumbagel/airstrik.py.git`

Edit `airstrikd.service`'s `ExecStart` and `WorkingDirectory` parameters to the location of airstrik_mongo.py and 
where you git cloned to.

Also set your python version in the `ExecStart` parameter (I use /usr/bin/python3.10, but just run `which python3`) to find out where python is installed. If you have multiple `python3`'s and aren't using the one your system aliases to `python3`, then change the python name in `install.sh` (line 12) from `python3` to `python3.12` or whatever.

Change the values in `config.yaml` to what you want (I would recommend just changing the lat/long to your current location to test)


Here's a quick description of the values in `config.yaml`:

| Item                       | Description                                                                                                                                                                                        |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| run_for                    | How long to run the script for in seconds. -1 is infinite. This is deprecated. (default=-1)                                                                                                                            |
| think_ahead                | How much time (in seconds) to simulate the aircraft's position ahead of where it is for the early warning system. (default=120)                                                                    |
| lat_lon_packet_age_max     | To prevent erratic values, airstrik uses an average from an older lat/long packet and current one. This is the maximum packet age. (default=10)                                                    |
| home                       | This stores your current lat/long to calculate various things. !!!This must be extremely accurate!!! (default=35.77031, -78.68078)                                                                 |              
| radius                     | The protection radius in km (you don't want to have planes within x kilometers) (default=20)                                                                                                       |
| min_alt                    | The minimum altitude an aircraft can be to not trigger an alarm in meters. (default=3000)                                                                                                          |
| remember                   | The maximum amount of time in seconds that an aircraft is kept around before deleting from RAM and saving to mongodb (default=45)                                                                  |
| dump1090_dir               | This should be kept at its current value if you use the installer. If you do not, set this to the directory of Flightaware's dump1090  (or Mutability's dump978)                                                             |
| json_speed                 | How much time (seconds) that dump1090 waits before getting updates. (default=0)                                                                                                                    |
| min_trip_length            | The minimum amount of time (seconds) we must receive packets from an aircraft for us to save it to mongodb. (we don't want a plane sending us one packet to be saved to the database) (default=90) |
| print_top_planes           | Print only this number of the closest planes. -1 is all planes. (default=-1)                                                                                                                                        |
| alarm_eta_trigger          | The amount of warning you want for the alarm to be called for a drone to enter your widest filter.|
|mongo-address| The address of the MongoDB database to connect to|
|filters| Write filters as a key-value in this format: <name>: [max <distance(km)>, max <alt(m)>]|

Here's a list of the command line arguments to `airstrik_mongo.py`:

|Item|Description|
|--------------|-----------|
|-q (--quiet)| Set the output mode to quiet, which turns off all non-error output |
|-c (--config) <FILE>| Set the directory or relative path to the configuration file (default config.yaml)|
|--no-dump| Don't dump the current data when run_for (config) is set to a non-infinite value. This is deprecated.|
|-d (--device) <DEVICE>| Set the RTLSDR device index or serial number to use if you have multiple receivers. Default is 0|
|--database-out <DATABASE>| Set the MongoDB database to dump data to (default airstrikdb)|
|--no-purge| Don't purge old data folders on startup. This is useful when you have multiple receivers and don't want to crash the other instance.|
|--log-mode|Print in a log mode instead of a auto-refreshing mode. This argument overrides -q/--quiet.|
|--no-start-dump| Don't start dump1090/dump978 and provide the directory where the data is.|
|--run-dump-978| Run dump978 insteaad of dump1090. This should be only used for receivers that are 978mhz.|


### Installation
There are two ways to install airstrik.py, Docker Compose and systemd. The

## systemd

Run `./install.sh` to install.

When this is done, confirm that 

1. mongod.service exists (`systemctl status mongod`)
2. airstrikd.service exists (`systemctl status airstrikd`)
3. dump1090 works (`cd` into its directory (the subfolder `dump1090`) and run (with the antenna plugged in) `./dump1090 --interactive`). If you see planes showing up, you are good to go!


Now, run `systemctl enable airstrikd && systemctl start airstrikd` to start up

After this, wait 10 seconds or so and check that it is running.

If the service crashed, post an issue with the output of `journalctl -e -u airstrikd` and I'll try to help.



## Docker Compose
