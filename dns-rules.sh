#!/bin/bash

/bin/sleep 5
/usr/sbin/ipconfig waitall

pf_config="/etc/pf.conf"

# Check if rules alreadu exists
if [ $(grep -lr "proto { udp, tcp } from en0 to any port 53" "$pf_config") ] ; then
    echo "Rules already added"
else
    echo "Adding rules to $pf_config"
    sed -i '' 's|dummynet-anchor "com\.apple\/\*"|dummynet-anchor "com.apple/*"\n\nPackets = "proto { udp, tcp } from en0 to any port 53"\nrdr pass log on lo0 $Packets -> 127.0.0.1\npass out on en0 route-to lo0 inet $Packets\n|' $pf_config
fi

echo "Starting pf with new rules and firewall enabled"
/sbin/pfctl -ef $pf_config
