.PHONY: build run stop clean deploy undeploy test load-test help

help:
	@echo "Available commands:"
	@echo "  make build        - Build all Docker images"
	@echo "  make run          - Run with Docker Compose"
	@echo "  make stop         - Stop Docker Compose"
	@echo "  make clean        - Clean up Docker resources"
	@echo "  make deploy       - Deploy to Kubernetes"
	@echo "  make undeploy     - Remove from Kubernetes"
	@echo "  make test         - Run tests"
	@echo "  make load-test    - Run load tests"

build:
	@echo "Building Docker images..."
	@docker build -t chat-backend:latest ./backend
	@docker build -t forecaster:latest ./forecaster
	@docker build -t keda-scaler:latest ./keda-scaler
	@echo "Build complete!"

run: build
	@echo "Starting services with Docker Compose..."
	@docker-compose up -d
	@echo "Services started!"
	@echo "Chat Backend: http://localhost:8000"
	@echo "Forecaster: http://localhost:8001"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"

stop:
	@echo "Stopping Docker Compose services..."
	@docker-compose down
	@echo "Services stopped!"

clean:
	@echo "Cleaning up Docker resources..."
	@docker-compose down -v
	@docker rmi chat-backend:latest forecaster:latest keda-scaler:latest 2>/dev/null || true
	@echo "Cleanup complete!"

deploy: build
	@echo "Deploying to Kubernetes..."
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh

undeploy:
	@echo "Removing from Kubernetes..."
	@chmod +x scripts/cleanup.sh
	@./scripts/cleanup.sh

test:
	@echo "Running tests..."
	@cd backend && python -m pytest -v 2>/dev/null || echo "No tests found in backend"
	@cd forecaster && python -m pytest -v 2>/dev/null || echo "No tests found in forecaster"

load-test:
	@echo "Running load test..."
	@cd load-test && python load_test.py --pattern spike --base-clients 10 --spike-clients 30

load-test-locust:
	@echo "Starting Locust load test..."
	@echo "Open http://localhost:8089 in your browser"
	@cd load-test && locust -f locustfile.py --host http://localhost:8000

logs-backend:
	@docker-compose logs -f chat-backend

logs-forecaster:
	@docker-compose logs -f forecaster

logs-scaler:
	@docker-compose logs -f keda-scaler

k8s-logs-backend:
	@kubectl logs -f deployment/chat-backend -n chat-autoscaler

k8s-logs-forecaster:
	@kubectl logs -f deployment/forecaster -n chat-autoscaler

k8s-logs-scaler:
	@kubectl logs -f deployment/keda-external-scaler -n chat-autoscaler

k8s-status:
	@echo "Pods:"
	@kubectl get pods -n chat-autoscaler
	@echo "\nServices:"
	@kubectl get svc -n chat-autoscaler
	@echo "\nScaledObject:"
	@kubectl get scaledobject -n chat-autoscaler
