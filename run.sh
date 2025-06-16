#!/bin/bash

# Arrête et supprime les anciens conteneurs (facultatif)
# docker rm -f mon_app_container 2>/dev/null || true

# Build l’image si elle n’existe pas
docker build -t lora-helium-map .

# Exécute le conteneur
docker run -it --rm \
    --name lora-map \
    -p 5000:5000 \
    lora-helium-map
