#!/bin/bash

SUBDOMAIN=$(echo "$1" | tr -d '\n' | tr -d '\r')  #Enlever le \n à la fin du read
PORT=5000
HOST="0.0.0.0"
MAX_RETRIES=10
RETRY_INTERVAL=2
GRACE_PERIOD=5

if [[ -z "$SUBDOMAIN" ]]; then
    echo "Usage: $0 <subdomain>"
    exit 1
fi


start_tunnel() {
    echo "Launching localtunnel on subdomain '$SUBDOMAIN'..."
    lt --port "$PORT" --subdomain "$SUBDOMAIN" --local-host "$HOST" &
    LT_PID=$!
}

check_tunnel() {
    # echo "Waiting ${GRACE_PERIOD}s before checking tunnel..."
    sleep "$GRACE_PERIOD"

    for ((i=1; i<=MAX_RETRIES; i++)); do
        # echo "Checking if tunnel is alive (attempt $i/$MAX_RETRIES)..."
        if curl -s "http://${SUBDOMAIN}.loca.lt/" | grep -q "OK"; then
            # echo "Tunnel is up and running!"
            return 0
        fi
        sleep "$RETRY_INTERVAL"
    done
    # echo "Tunnel failed to start after $MAX_RETRIES attempts."
    return 1
}

while true; do
    start_tunnel
    if check_tunnel; then
        # Attendre que le process lt se termine (ex: déconnexion)
        wait $LT_PID
        echo "Tunnel interrupted. Relaunching in 5 seconds..."
    else
        # Si le tunnel n'était pas accessible, tuer le process et relancer
        echo "Killing failed tunnel process..."
        kill $LT_PID 2>/dev/null
    fi
    sleep 5
done
