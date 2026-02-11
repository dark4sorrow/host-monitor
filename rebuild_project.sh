#!/bin/bash

# Set the absolute path so this script works from anywhere (cron, home dir, etc.)
PROJECT_DIR="/home/damurphy/docker_apps/host-monitor"

echo "Building Image..."
docker build -t host-monitor "$PROJECT_DIR"

echo "Stopping existing container..."
# Added "|| true" so the script doesn't crash if the container is already stopped
docker stop host-monitor || true

echo "Removing existing container..."
docker rm host-monitor || true

echo "Starting Container..."
docker run -d \
  --name host-monitor \
  --restart unless-stopped \
  -p 5005:5000 \
  -v "$PROJECT_DIR/config.json":/app/config.json \
  -v "$PROJECT_DIR/output":/app/output \
  host-monitor

echo "Done! Running on port 5005."