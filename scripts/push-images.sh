#!/bin/bash

set -e

# Configuration
REGISTRY=${DOCKER_REGISTRY:-""}
TAG=${IMAGE_TAG:-"latest"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Docker Registry Image Push Script${NC}"
echo "======================================"

# Check if registry is provided
if [ -z "$REGISTRY" ]; then
    echo -e "${YELLOW}No DOCKER_REGISTRY environment variable set.${NC}"
    echo "Usage: DOCKER_REGISTRY=yourusername ./scripts/push-images.sh"
    echo "   or: DOCKER_REGISTRY=myregistry.azurecr.io ./scripts/push-images.sh"
    read -p "Enter registry (e.g., 'yourusername' for Docker Hub): " REGISTRY
    if [ -z "$REGISTRY" ]; then
        echo -e "${RED}Registry is required!${NC}"
        exit 1
    fi
fi

# Build images first
echo -e "${GREEN}Building images...${NC}"
docker build -t chat-backend:${TAG} ./backend
docker build -t forecaster:${TAG} ./forecaster
docker build -t keda-scaler:${TAG} ./keda-scaler

# Tag images
echo -e "${GREEN}Tagging images for registry: ${REGISTRY}${NC}"
docker tag chat-backend:${TAG} ${REGISTRY}/chat-backend:${TAG}
docker tag forecaster:${TAG} ${REGISTRY}/forecaster:${TAG}
docker tag keda-scaler:${TAG} ${REGISTRY}/keda-scaler:${TAG}

# Push images
echo -e "${GREEN}Pushing images to registry...${NC}"
docker push ${REGISTRY}/chat-backend:${TAG}
docker push ${REGISTRY}/forecaster:${TAG}
docker push ${REGISTRY}/keda-scaler:${TAG}

echo -e "${GREEN}✅ Images pushed successfully!${NC}"
echo ""
echo "Update your k8s manifests with:"
echo "  image: ${REGISTRY}/chat-backend:${TAG}"
echo "  image: ${REGISTRY}/forecaster:${TAG}"
echo "  image: ${REGISTRY}/keda-scaler:${TAG}"

