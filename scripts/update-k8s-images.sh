#!/bin/bash

set -e

REGISTRY=${DOCKER_REGISTRY:-""}
TAG=${IMAGE_TAG:-"latest"}

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$REGISTRY" ]; then
    echo -e "${YELLOW}No DOCKER_REGISTRY set. Using local images.${NC}"
    echo "To use a registry: DOCKER_REGISTRY=yourusername $0"
    exit 0
fi

echo -e "${GREEN}Updating Kubernetes manifests with registry: ${REGISTRY}${NC}"

# Update chat-backend
sed -i.bak "s|image: chat-backend:.*|image: ${REGISTRY}/chat-backend:${TAG}|" k8s/ml-autoscaler/chat-backend.yaml
sed -i.bak "s|imagePullPolicy: IfNotPresent|imagePullPolicy: Always|" k8s/ml-autoscaler/chat-backend.yaml

# Update forecaster
sed -i.bak "s|image: forecaster:.*|image: ${REGISTRY}/forecaster:${TAG}|" k8s/ml-autoscaler/forecaster.yaml
sed -i.bak "s|imagePullPolicy: IfNotPresent|imagePullPolicy: Always|" k8s/ml-autoscaler/forecaster.yaml

# Update keda-scaler
sed -i.bak "s|image: keda-scaler:.*|image: ${REGISTRY}/keda-scaler:${TAG}|" k8s/ml-autoscaler/keda-scaler.yaml
sed -i.bak "s|imagePullPolicy: IfNotPresent|imagePullPolicy: Always|" k8s/ml-autoscaler/keda-scaler.yaml

# Clean up backup files
rm -f k8s/ml-autoscaler/*.yaml.bak

echo -e "${GREEN}✅ Kubernetes manifests updated!${NC}"
echo ""
echo "Images updated to:"
echo "  ${REGISTRY}/chat-backend:${TAG}"
echo "  ${REGISTRY}/forecaster:${TAG}"
echo "  ${REGISTRY}/keda-scaler:${TAG}"
echo ""
echo "Now run: ./scripts/deploy.sh"

