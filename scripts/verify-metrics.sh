#!/bin/bash

echo "🔍 Verifying Kubernetes metrics are available in Prometheus..."

PROMETHEUS_URL="http://localhost:9090"

# Check if we can connect to Prometheus
if ! curl -s "${PROMETHEUS_URL}/api/v1/query?query=up" > /dev/null; then
    echo "❌ Cannot connect to Prometheus at ${PROMETHEUS_URL}"
    echo "💡 Try running: kubectl port-forward -n monitoring service/prometheus 9090:9090"
    exit 1
fi

echo "✅ Connected to Prometheus"

# Check key metrics
metrics_to_check=(
    "kube_deployment_status_replicas"
    "kube_pod_container_resource_requests"
    "kube_pod_container_resource_limits"
    "kube_pod_status_phase"
    "node_memory_MemTotal_bytes"
    "node_cpu_seconds_total"
    "chat_messages_per_second"
)

echo ""
echo "📊 Checking metrics availability:"

for metric in "${metrics_to_check[@]}"; do
    response=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${metric}" | jq -r '.data.result | length')
    
    if [[ "$response" -gt 0 ]]; then
        echo "✅ ${metric} - Found ${response} series"
    else
        echo "❌ ${metric} - No data found"
    fi
done

echo ""
echo "🎯 Checking specific deployment metrics:"

# Check chat-backend deployment replicas specifically
deployment_replicas=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=kube_deployment_status_replicas{deployment=\"chat-backend\",namespace=\"ml-autoscaler\"}" | jq -r '.data.result[0].value[1] // "N/A"')

if [[ "$deployment_replicas" != "N/A" ]]; then
    echo "✅ chat-backend deployment replicas: ${deployment_replicas}"
else
    echo "❌ chat-backend deployment replicas: Not found"
fi

echo ""
echo "📝 Prometheus targets status:"
echo "Checking target health..."
unhealthy_targets=$(curl -s "${PROMETHEUS_URL}/api/v1/targets" | jq -r '.data.activeTargets[] | select(.health != "up") | "❌ \(.job) (\(.discoveredLabels.__address__)) - \(.lastError // "Unknown error")"')

if [[ -n "$unhealthy_targets" ]]; then
    echo "$unhealthy_targets"
else
    echo "✅ All targets are healthy"
fi

echo ""
echo "📊 Resource allocation metrics for chat-backend:"
chat_cpu_requests=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=kube_pod_container_resource_requests{namespace=\"ml-autoscaler\",container=\"chat-backend\",resource=\"cpu\"}" | jq -r '.data.result | length')
chat_memory_requests=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=kube_pod_container_resource_requests{namespace=\"ml-autoscaler\",container=\"chat-backend\",resource=\"memory\"}" | jq -r '.data.result | length')

if [[ "$chat_cpu_requests" -gt 0 ]]; then
    echo "✅ chat-backend CPU requests: Found ${chat_cpu_requests} series"
else
    echo "❌ chat-backend CPU requests: No data found"
fi

if [[ "$chat_memory_requests" -gt 0 ]]; then
    echo "✅ chat-backend Memory requests: Found ${chat_memory_requests} series"  
else
    echo "❌ chat-backend Memory requests: No data found"
fi

echo ""
echo "📊 Node-level resource metrics:"
node_memory=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=node_memory_MemTotal_bytes" | jq -r '.data.result | length')
node_cpu=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=node_cpu_seconds_total" | jq -r '.data.result | length')

if [[ "$node_memory" -gt 0 ]]; then
    echo "✅ Node memory metrics: Found ${node_memory} series"
else
    echo "❌ Node memory metrics: No data found"
fi

if [[ "$node_cpu" -gt 0 ]]; then
    echo "✅ Node CPU metrics: Found ${node_cpu} series"
else
    echo "❌ Node CPU metrics: No data found"
fi

echo ""
echo "🌐 Grafana Dashboard URLs:"
echo "Main Dashboard: http://localhost:3000/d/predictive-scaling/predictive-autoscaling-dashboard"
echo "Explore Metrics: http://localhost:3000/explore"
