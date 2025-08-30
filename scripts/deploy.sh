#!/bin/bash

set -e

echo "Deploying to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "kubectl could not be found. Please install kubectl first."
    exit 1
fi

# Check if KEDA is installed
if ! kubectl get deployment -n keda keda-operator &> /dev/null; then
    echo "KEDA is not installed. Installing KEDA..."
    kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.12.0/keda-2.12.0.yaml
    echo "Waiting for KEDA to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/keda-operator -n keda
fi

# Create namespaces
echo "Creating namespaces..."
kubectl apply -f k8s/namespaces.yaml

# Deploy monitoring services first (dependencies for application services)
echo "Deploying monitoring services..."
kubectl apply -f k8s/monitoring/

# Deploy application services
echo "Deploying Redis..."
kubectl apply -f k8s/ml-autoscaler/redis.yaml

# Wait for monitoring services to be ready
echo "Waiting for monitoring services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring
kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring
kubectl wait --for=condition=available --timeout=300s deployment/kube-state-metrics -n monitoring
kubectl wait --for=condition=ready --timeout=300s pod -l app=node-exporter -n monitoring

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/redis -n ml-autoscaler

# Deploy chat backend
echo "Deploying chat backend..."
kubectl apply -f k8s/ml-autoscaler/chat-backend.yaml

# Deploy forecaster
echo "Deploying forecaster..."
kubectl apply -f k8s/ml-autoscaler/forecaster.yaml

# Deploy KEDA scaler
echo "Deploying KEDA external scaler..."
kubectl apply -f k8s/ml-autoscaler/keda-scaler.yaml

# Wait for all deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/chat-backend -n ml-autoscaler
kubectl wait --for=condition=available --timeout=300s deployment/forecaster -n ml-autoscaler
kubectl wait --for=condition=available --timeout=300s deployment/keda-external-scaler -n ml-autoscaler

# Deploy KEDA ScaledObject
echo "Deploying KEDA ScaledObject..."
kubectl apply -f k8s/ml-autoscaler/keda-scaledobject.yaml

echo "Deployment complete!"
echo ""
echo "Service URLs (if using LoadBalancer):"
echo "- Chat Backend: http://$(kubectl get svc chat-backend -n ml-autoscaler -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8000"
echo "- Prometheus: http://$(kubectl get svc prometheus -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):9090"
echo "- Grafana: http://$(kubectl get svc grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):3000"
echo ""
echo "Default Grafana credentials: admin/admin"
echo ""
echo "To view logs:"
echo "kubectl logs -f deployment/chat-backend -n ml-autoscaler"
echo "kubectl logs -f deployment/forecaster -n ml-autoscaler"
echo "kubectl logs -f deployment/keda-external-scaler -n ml-autoscaler"
