#!/bin/bash
set -e

# Activer le venv
source venv/bin/activate

echo "🔧 Initialisation de la configuration..."

# Lire latitude et longitude s'ils ne sont pas déjà définis
if [ ! -f configs/.latitude ]; then
  read -p "Latitude de votre end-node (ex: 45.70377): " latitude
  echo "$latitude" > configs/.latitude
else
  echo "✅ Latitude déjà définie : $(cat configs/.latitude)"
fi

if [ ! -f configs/.longitude ]; then
  read -p "Longitude de votre end-node (ex: 13.7204): " longitude
  echo "$longitude" > configs/.longitude
else
  echo "✅ Longitude déjà définie : $(cat configs/.longitude)"
fi

# Lire le subdomain si absent
if [ ! -f configs/.subdomain ]; then
  read -p "Nom du subdomain localtunnel : " subdomain
  echo "$subdomain" > configs/.subdomain
else
  echo "✅ Subdomain déjà défini : $(cat configs/.subdomain)"
fi

echo "🚀 Lancement de l'application..."
python3 main.py --logs
