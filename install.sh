curl -fsSL https://pgp.mongodb.com/server-6.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg \
   --dearmor
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo cp airstrikd.service /etc/systemd/system/airstrikd.service
sudo chmod 644 /etc/systemd/system/airstrikd.service
systemctl daemon-reload
python3 -m pip install -r requirements.txt
echo "Run systemctl start airstrikd to begin"