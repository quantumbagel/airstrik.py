FROM ubuntu:20.04

# Install system dependencies
RUN DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt install -y git build-essential fakeroot sudo debhelper librtlsdr-dev pkg-config libncurses5-dev gnupg librtlsdr-dev libusb-dev python3 python3-dev python3-pip rtl-sdr

# Create workdir
WORKDIR /opt/ads-b/
COPY ./* /opt/ads-b/
COPY ./d0/config.yaml /opt/ads-b/the-real-config.yaml
RUN python3 -m pip install -r requirements.txt
RUN git clone https://github.com/flightaware/dump1090.git
RUN cd dump1090 && make RTLSDR=yes
RUN cd ..
CMD python3 airstrik_mongo.py --log-mode -d 0 --database-out airstrik-py