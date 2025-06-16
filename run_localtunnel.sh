#!/bin/bash

while true; do
    echo "Launching localtunnel..."
    lt --port 5000 --subdomain $1 --local-host 0.0.0.0
    echo "Tunnel interrupted. Relaunching in 5 seconds..."
    sleep 5
done