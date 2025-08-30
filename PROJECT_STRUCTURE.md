# 📁 Project Structure

This document outlines the organized structure of the KEDA ML Autoscaler project.

## 🏗️ Root Directory

```
keda-ml-autoscaler/
├── README.md                    # Main project documentation
├── LICENSE                      # MIT license
├── Makefile                     # Build and deployment commands
├── docker-compose.yml           # Local development setup
├── requirements-dev.txt         # Development dependencies
├── test-client.html            # WebSocket test client
└── .gitignore                  # Enhanced git ignore patterns
```

## 📚 Documentation (`docs/`)

```
docs/
├── README.md                    # Documentation index
├── architecture/
│   └── project.md              # System architecture overview
├── deployment/
│   └── kubernetes-deployment.md # K8s deployment guide
├── guides/
│   ├── MINIKUBE_MONITORING_GUIDE.md # Minikube setup guide
│   └── MONITORING_STATUS.md    # Monitoring stack status
└── images/
    ├── architecture-diagram.png # System architecture diagram
    └── system-overview.png     # System overview visualization
```

## 🐳 Application Services

```
backend/                        # Chat backend service
├── app.py                      # FastAPI WebSocket server
├── Dockerfile                  # Container definition
└── requirements.txt            # Python dependencies

forecaster/                     # ML forecasting service
├── forecaster.py               # Prophet-based forecaster
├── Dockerfile                  # Container definition
└── requirements.txt            # Python dependencies

keda-scaler/                    # KEDA external scaler
├── scaler.py                   # gRPC external scaler
├── externalscaler.proto        # Protocol buffer definition
├── generate_proto.sh           # Proto generation script
├── Dockerfile                  # Container definition
└── requirements.txt            # Python dependencies
```

## ☸️ Kubernetes Manifests (`k8s/`)

```
k8s/
├── namespaces.yaml             # Namespace definitions
├── ml-autoscaler/              # Main application manifests
│   ├── chat-backend.yaml       # Chat backend deployment
│   ├── forecaster.yaml         # Forecaster deployment
│   ├── keda-scaler.yaml        # KEDA external scaler
│   ├── keda-scaledobject.yaml  # KEDA scaling configuration
│   └── redis.yaml              # Redis deployment
└── monitoring/                 # Monitoring stack manifests
    ├── prometheus.yaml         # Prometheus deployment
    ├── grafana.yaml            # Grafana deployment
    ├── kube-state-metrics.yaml # K8s metrics exporter
    └── node-exporter.yaml      # Node metrics exporter
```

## 📊 Monitoring Configuration (`monitoring/`)

```
monitoring/
├── prometheus.yml              # Prometheus configuration
└── grafana/
    ├── dashboards/
    │   └── dashboard-provider.yml # Dashboard provider config
    ├── datasources/
    │   └── prometheus.yml      # Prometheus datasource config
    └── dashboard-files/
        └── predictive-scaling.json # Main dashboard
```

## 🧪 Load Testing (`load-test/`)

```
load-test/
├── requirements.txt            # Testing dependencies
├── http_load_test.py          # HTTP-based load testing (recommended)
├── load_test.py               # WebSocket-based load testing
└── locustfile.py              # Locust load testing configuration
```

## 🚀 Deployment Scripts (`scripts/`)

```
scripts/
├── build.sh                   # Build Docker images
├── deploy.sh                  # Deploy to Kubernetes
├── cleanup.sh                 # Clean up deployments
├── push-images.sh             # Push images to registry
├── update-k8s-images.sh       # Update K8s image references
├── deploy-monitoring.sh       # Deploy monitoring stack
└── verify-metrics.sh          # Verify metrics collection
```

## 🎯 Key Improvements Made

### ✅ Documentation Organization
- **Centralized docs/**: All documentation moved to organized structure
- **Clear categorization**: Architecture, guides, deployment, images
- **Enhanced README**: Professional presentation with badges and clear sections
- **Documentation index**: Easy navigation between documents

### ✅ File Structure Cleanup
- **Removed duplicates**: Eliminated duplicate K8s manifests
- **Logical grouping**: Services, configs, and docs properly organized
- **Clean root directory**: Only essential files at project root
- **Descriptive naming**: Images renamed with clear purposes

### ✅ Enhanced Configuration
- **Comprehensive .gitignore**: Added patterns for Python, Node, Docker, K8s
- **Organized K8s manifests**: Separated application and monitoring configs
- **Clear service structure**: Each service has its own directory with all needed files

### ✅ Professional Presentation
- **Visual README**: Added badges, emojis, and clear sections
- **Quick start guides**: Easy-to-follow setup instructions
- **Troubleshooting section**: Common issues and solutions
- **Performance metrics**: Highlighted optimization achievements

## 🔗 Navigation

- **Main Documentation**: [README.md](README.md)
- **Architecture Details**: [docs/architecture/project.md](docs/architecture/project.md)
- **Deployment Guide**: [docs/deployment/kubernetes-deployment.md](docs/deployment/kubernetes-deployment.md)
- **Monitoring Setup**: [docs/guides/MONITORING_STATUS.md](docs/guides/MONITORING_STATUS.md)
- **Development Guide**: [docs/guides/MINIKUBE_MONITORING_GUIDE.md](docs/guides/MINIKUBE_MONITORING_GUIDE.md)

---

**The project is now organized for professional presentation and easy maintenance! 🎉**
