#!/bin/bash
set -e

# Activer l’environnement virtuel
source venv/bin/activate

read -p "Latitude of the end-node (ex: 45.70377): " latitude
echo "$latitude" > configs/.latitude

read -p "Longitude of the end-node (ex: 13.7204): " longitude
echo "$longitude" > configs/.longitude

read -p "Subdomain name for localtunnel : " subdomain
echo "$subdomain" > configs/.subdomain

# Lancer le script principal
python3 main.py --logs
