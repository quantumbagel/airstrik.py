sudo apt-get update
sudo apt-get install -y mongodb-org
sudo cp airstrikd.service /etc/systemd/system/airstrikd.service
sudo chmod 644 /etc/systemd/system/airstrikd.service
systemctl daemon-reload
python3 -m pip install -r requirements.txt
echo "Run systemctl start airstrikd to begin"