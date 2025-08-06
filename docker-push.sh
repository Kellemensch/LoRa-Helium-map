#!/bin/bash

DOCKERHUB_USER="kellemensch"
APP_NAME="lora-helium-map"
TAG="marconilab_era5"
DOCKERFILE_APP="Dockerfile.dev"

# Optionnel : stop on error
set -e

echo "Building image: $APP_NAME"
docker build --no-cache -f $DOCKERFILE_APP -t $DOCKERHUB_USER/$APP_NAME:$TAG .

echo "Pushing image: $DOCKERHUB_USER/$APP_NAME:$TAG"
docker push $DOCKERHUB_USER/$APP_NAME:$TAG

echo "All images pushed successfully!"
