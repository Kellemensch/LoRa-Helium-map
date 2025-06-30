#!/bin/bash

echo "Initializing configuration..."

# Lire latitude et longitude s'ils ne sont pas déjà définis
if [ ! -f configs/.latitude ]; then
  read -p "Latitude of the end-node (ex: 45.70377): " latitude
  echo "$latitude" > configs/.latitude
else
  echo "Latitude already defined : $(cat configs/.latitude)"
fi

if [ ! -f configs/.longitude ]; then
  read -p "Longitude of the end-node (ex: 13.7204): " longitude
  echo "$longitude" > configs/.longitude
else
  echo "Longitude already defined : $(cat configs/.longitude)"
fi

# Lire le subdomain si absent
if [ ! -f configs/.subdomain ]; then
  read -p "Subdomain name for localtunnel : " subdomain
  echo "$subdomain" > configs/.subdomain
else
  echo "Subdomain already defined : $(cat configs/.subdomain)"
fi

echo "Starting containers with docker-compose..."

# Pour que le dossier output soit non root
export LOCAL_UID=$(id -u)
export LOCAL_GID=$(id -g)

docker compose pull
docker compose up -d

echo "Logs for app: docker logs -f lora-map"
echo "Logs for ollama: docker logs -f ollama-server"
echo "Stop everything with: docker compose down"
