sudo apt install curl gnupg librtlsdr-dev libusb-dev
curl -fsSL https://pgp.mongodb.com/server-6.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg \
   --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo apt-get install -f
sudo cp airstrikd.service /etc/systemd/system/airstrikd.service
sudo chmod 644 /etc/systemd/system/airstrikd.service
sudo systemctl daemon-reload
python3 -m pip install -r requirements.txt
git clone https://github.com/flightaware/dump1090.git
cd dump1090 || exit
make RTLSDR=yes
echo "Run systemctl start airstrikd to begin"