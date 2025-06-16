#!/bin/bash

UID_LOCAL=$(id -u)
GID_LOCAL=$(id -g)

docker build -t lora-helium-map .

docker run -it --rm \
  -p 5000:5000 \
  -v "$(pwd)/output:/app/output" \
  -e HOST_UID=$UID_LOCAL \
  -e HOST_GID=$GID_LOCAL \
  lora-helium-map
