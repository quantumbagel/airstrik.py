curl -fsSL https://pgp.mongodb.com/server-6.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg \
   --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo cp airstrikd.service /etc/systemd/system/airstrikd.service
sudo chmod 644 /etc/systemd/system/airstrikd.service
systemctl daemon-reload
python3 -m pip install -r requirements.txt
echo "Run system

ctl start airstrikd to begin"