#!/bin/bash
#v0.7

CERT_SERVER=<user>@acme-dns.lab.frnot.com
CERT_DIR="/etc/cockpit/ws-certs.d"
CMD="cat $CERT_DIR/key.pem $CERT_DIR/cert.pem > $CERT_DIR/50-le.cert && systemctl restart cockpit"

verbose=false
force=false

run() {
        if [ "$force" = true ]; then
                printf "\"--force\" specified, renewing certs.\n"
                renew
        elif [ $(new_certs_available) = "TRUE" ]; then
                if [ "$verbose" = true ]; then
                        printf "New cert found, renewing.\n"
                fi
                renew
        else
                if [ "$verbose" = true ]; then
                        printf "No new certificates found, exiting.\n"
                fi
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
        if [ "$verbose" = true ]; then
                sftp $CERT_SERVER:/* $CERT_DIR
        else
                sftp $CERT_SERVER:/* $CERT_DIR >/dev/null
        fi

        printf "Executing: $CMD\n"
        eval $CMD
}

while test $# -gt 0; do
    case "$1" in
        -f|--force)
            force=true
            shift
            ;;
        -v)
            verbose=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

run $@
