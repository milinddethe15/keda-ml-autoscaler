# Kubernetes Manifests

This directory contains Kubernetes manifests organized by namespace for better separation of concerns.

## Directory Structure

```
k8s/
├── namespaces.yaml           # Namespace definitions
├── ml-autoscaler/           # Application services
│   ├── chat-backend.yaml    # Chat backend service and deployment
│   ├── forecaster.yaml      # ML forecaster service and deployment
│   ├── keda-scaler.yaml     # KEDA external scaler service and deployment
│   ├── redis.yaml           # Redis cache service and deployment
│   └── keda-scaledobject.yaml # KEDA ScaledObject for autoscaling
└── monitoring/              # Monitoring and observability services
    ├── prometheus.yaml      # Prometheus monitoring service
    ├── grafana.yaml         # Grafana dashboard service
    ├── node-exporter.yaml   # Node metrics exporter
    └── kube-state-metrics.yaml # Kubernetes state metrics

```

## Namespaces

### ml-autoscaler
Contains the core application services:
- **chat-backend**: Main application service that handles chat requests
- **forecaster**: ML service that predicts future load based on historical data
- **keda-scaler**: External scaler that provides predictions to KEDA
- **redis**: Cache and message broker
- **keda-scaledobject**: KEDA configuration for predictive autoscaling

### monitoring
Contains observability and monitoring services:
- **prometheus**: Metrics collection and storage
- **grafana**: Visualization and dashboards
- **node-exporter**: Node-level system metrics
- **kube-state-metrics**: Kubernetes object state metrics

## Deployment

Deploy in the following order:

1. **Namespaces**: `kubectl apply -f namespaces.yaml`
2. **Monitoring services**: `kubectl apply -f monitoring/`
3. **Application services**: `kubectl apply -f ml-autoscaler/`

## Cross-Namespace Communication

Services communicate across namespaces using fully qualified domain names (FQDN):
- Forecaster → Prometheus: `prometheus.monitoring.svc.cluster.local:9090`
- Grafana → Prometheus: `prometheus.monitoring.svc.cluster.local:9090`
- KEDA → External Scaler: `keda-external-scaler.ml-autoscaler.svc.cluster.local:6000`

## Benefits of This Organization

1. **Separation of Concerns**: Application logic is separated from monitoring infrastructure
2. **Security**: Different RBAC policies can be applied to each namespace
3. **Resource Management**: Resource quotas and limits can be set per namespace
4. **Easier Management**: Clear boundaries make it easier to manage and troubleshoot services
5. **Scalability**: Each namespace can be managed independently
