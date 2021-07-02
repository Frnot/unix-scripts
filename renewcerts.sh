#!/bin/bash
#v0.6

CERT_SERVER=<user>@acme-dns.lab.frnot.com
CERT_DIR="/etc/cockpit/ws-certs.d"
CMD="cat $CERT_DIR/key.pem $CERT_DIR/cert.pem > $CERT_DIR/50-le.cert && systemctl restart cockpit"

run() {
        if [ ! -z $1 ] && [ $1 = "--force" ]; then
                printf "\"--force\" specified, renewing certs.\n"
                renew
        elif [ $(new_certs_available) = "TRUE" ]; then
                printf "New cert found, renewing.\n"
                renew
        else
                printf "No new certificates found, exiting.\n"
        fi
}

new_certs_available() {
        OLDHASH=$(sha256sum < $CERT_DIR/cert.pem)
        sftp $CERT_SERVER:/cert.pem /tmp/tempcert.pem >/dev/null
        NEWHASH=$(sha256sum < /tmp/tempcert.pem)
        rm /tmp/tempcert.pem

        if [ -n "$NEWHASH" ] && [[ -z "$OLDHASH" || "$OLDHASH" != "$NEWHASH" ]]; then
                printf "TRUE"
        else
                printf "FALSE"
        fi
}

renew() {
        sftp $CERT_SERVER:/* $CERT_DIR

        printf "Executing: $CMD\n"
        eval $CMD
}

run $@
