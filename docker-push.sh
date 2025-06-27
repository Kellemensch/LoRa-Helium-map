#!/bin/bash

DOCKERHUB_USER="kellemensch"
APP_NAME="lora-helium-map"
# OLLAMA_NAME="ollama"
TAG="latest"
DOCKERFILE_APP="Dockerfile.dev"
# DOCKERFILE_OLLAMA="Dockerfile.ollama"

# Optionnel : stop on error
set -e

echo "Building image: $APP_NAME"
docker build --no-cache -f $DOCKERFILE_APP -t $DOCKERHUB_USER/$APP_NAME:$TAG .

echo "Pushing image: $DOCKERHUB_USER/$APP_NAME:$TAG"
docker push $DOCKERHUB_USER/$APP_NAME:$TAG

# if [ -f $DOCKERFILE_OLLAMA ]; then
#   echo "Building image: $OLLAMA_NAME"
#   docker build -f $DOCKERFILE_OLLAMA -t $DOCKERHUB_USER/$OLLAMA_NAME:$TAG .
  
#   echo "Pushing image: $DOCKERHUB_USER/$OLLAMA_NAME:$TAG"
#   docker push $DOCKERHUB_USER/$OLLAMA_NAME:$TAG
# fi

echo "All images pushed successfully!"
