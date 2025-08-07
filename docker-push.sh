#!/bin/bash

# Arrêt sur erreur
set -e

# === CONFIG ===
DOCKERHUB_USER="kellemensch"
APP_NAME="lora-helium-map"
DOCKERFILE_APP="Dockerfile.dev"

# Vérifie que le tag version est passé en argument
if [ -z "$1" ]; then
  echo "Usage: $0 <version-tag>"
  echo "Example: $0 v1.0.0"
  exit 1
fi

VERSION_TAG=$1

# === BUILD & TAG ===
echo "Building image: $DOCKERHUB_USER/$APP_NAME:$VERSION_TAG"
docker build --no-cache -f $DOCKERFILE_APP -t $DOCKERHUB_USER/$APP_NAME:$VERSION_TAG .

echo "Tagging image as latest"
docker tag $DOCKERHUB_USER/$APP_NAME:$VERSION_TAG $DOCKERHUB_USER/$APP_NAME:latest

# === PUSH ===
echo "Pushing versioned image: $DOCKERHUB_USER/$APP_NAME:$VERSION_TAG"
docker push $DOCKERHUB_USER/$APP_NAME:$VERSION_TAG

echo "Pushing latest tag: $DOCKERHUB_USER/$APP_NAME:latest"
docker push $DOCKERHUB_USER/$APP_NAME:latest

echo "✅ All images pushed successfully!"
