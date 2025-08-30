#!/bin/bash

set -e

echo "🚀 Deploying monitoring stack with Kubernetes metrics support..."

# Create namespaces if they don't exist
kubectl apply -f k8s/namespaces.yaml

# Deploy all monitoring services
echo "📊 Deploying monitoring stack..."
kubectl apply -f k8s/monitoring/

# Wait for monitoring services to be ready
echo "⏳ Waiting for kube-state-metrics to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=kube-state-metrics -n monitoring --timeout=60s

echo "⏳ Waiting for node-exporter to be ready..."
kubectl wait --for=condition=ready pod -l app=node-exporter -n monitoring --timeout=60s

echo "⏳ Waiting for Prometheus to be ready..."
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=60s

echo "⏳ Waiting for Grafana to be ready..."
kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=60s

# Get service URLs
echo ""
echo "✅ Monitoring stack deployed successfully!"
echo ""
echo "📊 Access your monitoring services:"
echo "Prometheus: $(kubectl get service prometheus -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'localhost'):9090"
echo "Grafana:    $(kubectl get service grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'localhost'):3000"
echo ""
echo "📝 Grafana credentials: admin/admin"
echo ""
echo "🔍 To verify metrics are working:"
echo "1. Open Prometheus UI and check targets are 'UP'"
echo "2. Query 'kube_deployment_status_replicas' to see deployment metrics"
echo "3. Query 'container_memory_usage_bytes' to see container metrics"
echo "4. Open Grafana dashboard 'Predictive Autoscaling Dashboard'"
echo ""

# Optional: Port forward for local development
if [[ "${1}" == "--port-forward" ]]; then
    echo "🔗 Starting port forwarding..."
    echo "Prometheus will be available at: http://localhost:9090"
    echo "Grafana will be available at: http://localhost:3000"
    echo "Press Ctrl+C to stop port forwarding"
    
    kubectl port-forward -n monitoring service/prometheus 9090:9090 &
    kubectl port-forward -n monitoring service/grafana 3000:3000 &
    
    wait
fi
