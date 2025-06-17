#!/bin/bash

IMAGE_NAME="lora-helium-map"
CONTAINER_NAME="lora-map"

echo "🔧 Initializing configuration..."

# # Lire latitude et longitude s'ils ne sont pas déjà définis
# if [ ! -f configs/.latitude ]; then
#   read -p "Latitude of the end-node (ex: 45.70377): " latitude
#   echo "$latitude" > configs/.latitude
# else
#   echo "✅ Latitude already defined : $(cat configs/.latitude)"
# fi

# if [ ! -f configs/.longitude ]; then
#   read -p "Longitude of the end-node (ex: 13.7204): " longitude
#   echo "$longitude" > configs/.longitude
# else
#   echo "✅ Longitude already defined : $(cat configs/.longitude)"
# fi

# # Lire le subdomain si absent
# if [ ! -f configs/.subdomain ]; then
#   read -p "Subdomain name for localtunnel : " subdomain
#   echo "$subdomain" > configs/.subdomain
# else
#   echo "✅ Subdomain already defined : $(cat configs/.subdomain)"
# fi

UID_LOCAL=$(id -u)
GID_LOCAL=$(id -g)

docker build -t "$IMAGE_NAME" .

# docker run -d --rm \
#   -p 5000:5000 \
#   -v "$(pwd)/output:/app/output" \
#   -e HOST_UID=$UID_LOCAL \
#   -e HOST_GID=$GID_LOCAL \
#   --dns 8.8.8.8 \
#   --name "$CONTAINER_NAME" \
#   "$IMAGE_NAME"

echo "Logs can be seen with : docker logs -f $CONTAINER_NAME"
echo "🛑 Stop with : docker stop $CONTAINER_NAME"
