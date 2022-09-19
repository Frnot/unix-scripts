#!/bin/bash
# v1.1

# This script requires inotify-tools
# apt install inotify-tools

# Create the following system file
# enable it with: systemctl enable --now autochmod.service

#### /etc/systemd/system/autochmod.service ###
: <<'END'
[Unit]
Description= Automatic permission handler

[Service]
Type=simple
ExecStart=/bin/bash /usr/bin/autochmod.sh
Restart=always

[Install]
WantedBy=multi-user.target
END
####################################################

inotifywait -mr -e create --format '%w%f' /vault /scratch |
    while read FILE; do
        chmod 770 "$FILE"
    done
