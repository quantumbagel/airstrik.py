#!/bin/bash
echo "Starting dump1090..."
rm -rf dump1090/airstrik_data_runner_0
mkdir dump1090/airstrik_data_runner_0
sudo ./dump1090/dump1090 --write-json airstrik_data_runner_0 --write-json-every 0 --quiet &
python3 airstrik_mongo.py --no-start-dump1090 airstrik_data_runner_0 --no-purge --database-out airstrikd0_out --log-mode
