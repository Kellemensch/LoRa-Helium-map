#!/bin/bash

SUBDOMAIN=$(echo "$1" | tr -d '\n' | tr -d '\r')
PORT=5000
HOST="0.0.0.0"
MAX_RETRIES=5
RETRY_INTERVAL=2
GRACE_PERIOD=5
LOCALTUNNEL_CMD="lt"  # ou "/usr/local/bin/lt" si besoin

if [[ -z "$SUBDOMAIN" ]]; then
    echo "Usage: $0 <subdomain>"
    exit 1
fi

cleanup() {
    if [[ -n "$LT_PID" ]]; then
        kill "$LT_PID" 2>/dev/null
        wait "$LT_PID" 2>/dev/null
    fi
}

start_tunnel() {
    cleanup  # Nettoyer les anciens processus avant de démarrer
    echo "$(date) - Launching localtunnel on subdomain '$SUBDOMAIN'..."
    $LOCALTUNNEL_CMD --port "$PORT" --subdomain "$SUBDOMAIN" --local-host "$HOST" > /dev/null 2>&1 &
    LT_PID=$!
    disown $LT_PID  # Empêcher le shell d'attendre le processus
}

check_tunnel() {
    sleep "$GRACE_PERIOD"
    
    local attempts=0
    while [[ $attempts -lt $MAX_RETRIES ]]; do
        if curl -s --max-time 5 "http://${SUBDOMAIN}.loca.lt/" | grep -q "OK"; then
            return 0
        fi
        sleep "$RETRY_INTERVAL"
        attempts=$((attempts+1))
    done
    return 1
}

# Capturer Ctrl+C pour nettoyer proprement
trap cleanup EXIT

while true; do
    start_tunnel
    
    if check_tunnel; then
        echo "$(date) - Tunnel is up and running"
        # Attendre que le tunnel se termine (ou vérifier périodiquement)
        while kill -0 "$LT_PID" 2>/dev/null; do
            sleep 60
            # Vérifier périodiquement que le tunnel répond toujours
            if ! curl -s --max-time 5 "http://${SUBDOMAIN}.loca.lt/" | grep -q "OK"; then
                echo "$(date) - Tunnel seems down, restarting..."
                break
            fi
        done
    else
        echo "$(date) - Tunnel failed to start after $MAX_RETRIES attempts"
    fi
    
    cleanup
    echo "$(date) - Restarting tunnel in 5 seconds..."
    sleep 5
done