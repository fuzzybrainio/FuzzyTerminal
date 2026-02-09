#!/bin/bash

# FuzzyTerminal Launch Script
# This script builds and runs FuzzyTerminal inside a Docker container.

IMAGE_NAME="fuzzyterminal"

# Build the docker image if it doesn't exist or if requested
if [ -z "$(sudo docker images -q $IMAGE_NAME 2> /dev/null)" ] || [ "$1" = "--build" ]; then
    echo "Building FuzzyTerminal Docker image..."
    sudo docker build -t $IMAGE_NAME .
    if [ "$1" = "--build" ]; then
        shift
    fi
fi

# Ensure config directory exists on host
mkdir -p "$HOME/.fuzzyterminal"

# Run the docker container interactively
# We mount the host's .fuzzyterminal directory to persist configuration and history
# We also mount the current directory to allow the terminal to interact with local files if needed
sudo docker run -it --rm \
    -v "$HOME/.fuzzyterminal:/root/.fuzzyterminal" \
    -v "$(pwd):/app/workdir" \
    -w /app/workdir \
    $IMAGE_NAME "$@"
