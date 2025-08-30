#!/bin/bash

echo "Cleaning up Kubernetes resources..."

# Delete ScaledObject first to avoid scaling issues
kubectl delete -f k8s/ml-autoscaler/keda-scaledobject.yaml --ignore-not-found=true

# Delete application services
echo "Removing application services..."
kubectl delete -f k8s/ml-autoscaler/ --ignore-not-found=true

# Delete monitoring services
echo "Removing monitoring services..."
kubectl delete -f k8s/monitoring/ --ignore-not-found=true

# Delete namespaces (this will delete everything in them)
echo "Removing namespaces..."
kubectl delete -f k8s/namespaces.yaml --ignore-not-found=true

echo "Cleanup complete!"

# Optional: Remove KEDA if specified
if [ "$1" == "--remove-keda" ]; then
    echo "Removing KEDA..."
    kubectl delete -f https://github.com/kedacore/keda/releases/download/v2.12.0/keda-2.12.0.yaml
    echo "KEDA removed!"
fi
