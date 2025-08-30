#!/bin/bash

set -e

echo "Building Docker images..."

# Build chat backend
echo "Building chat-backend..."
docker build -t chat-backend:latest ./backend

# Build forecaster
echo "Building forecaster..."
docker build -t forecaster:latest ./forecaster

# Build KEDA scaler
echo "Building keda-scaler..."
docker build -t keda-scaler:latest ./keda-scaler

echo "All images built successfully!"

# Optional: Push to registry if specified
if [ "$1" == "--push" ]; then
    REGISTRY=${DOCKER_REGISTRY:-"localhost:5000"}
    echo "Pushing images to $REGISTRY..."
    
    docker tag chat-backend:latest $REGISTRY/chat-backend:latest
    docker tag forecaster:latest $REGISTRY/forecaster:latest
    docker tag keda-scaler:latest $REGISTRY/keda-scaler:latest
    
    docker push $REGISTRY/chat-backend:latest
    docker push $REGISTRY/forecaster:latest
    docker push $REGISTRY/keda-scaler:latest
    
    echo "Images pushed successfully!"
fi
