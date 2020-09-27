FROM phusion/baseimage:bionic-1.0.0

# Use baseimage-docker's init system:
CMD ["/sbin/my_init"]

# Install dependencies:
RUN apt-get update \
 && apt-get install -y \
    bash curl sudo wget \
    python3 unzip sed \
    python3-pip \
    systemd golang \
 && pip3 install \
    telethon cryptg \
    pillow aiohttp \
    hachoir \
 && curl -s https://raw.githubusercontent.com/oneindex/script/master/gclone.sh | sudo bash

# Clean up APT:
RUN apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set work dir:
WORKDIR /home

# Create required dirs:
RUN mkdir -p /home/.config/rclone/ \
 && mkdir -p scriptdir/

# Copy files:
COPY start /home/
COPY tg_channel_downloader.py /home/scriptdir/

# Run startup script:
CMD bash /home/start