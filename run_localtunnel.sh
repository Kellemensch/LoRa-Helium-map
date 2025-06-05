#!/bin/bash

while true; do
    echo "Launching localtunnel..."
    npx lt --port 5000 --subdomain marconilabictp
    echo "Tunnel interrupted. Relaunching in 5 seconds..."
    sleep 5
done