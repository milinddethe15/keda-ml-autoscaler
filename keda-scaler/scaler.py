import asyncio
import json
import logging
import os
from concurrent import futures
from datetime import datetime
from typing import Iterator

import grpc
import requests
from google.protobuf import empty_pb2

import externalscaler_pb2
import externalscaler_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FORECASTER_URL = os.getenv("FORECASTER_URL", "http://forecaster:8001")
METRIC_NAME = os.getenv("METRIC_NAME", "chat_messages_per_second")
FORECAST_MINUTES = int(os.getenv("FORECAST_MINUTES", "5"))
TARGET_VALUE = float(os.getenv("TARGET_VALUE", "10"))  # Messages per pod
MIN_REPLICAS = int(os.getenv("MIN_REPLICAS", "1"))
MAX_REPLICAS = int(os.getenv("MAX_REPLICAS", "20"))


class ExternalScaler(externalscaler_pb2_grpc.ExternalScalerServicer):
    
    def IsActive(self, request, context):
        try:
            response = requests.post(
                f"{FORECASTER_URL}/forecast",
                json={
                    "metric_name": METRIC_NAME,
                    "horizon_minutes": FORECAST_MINUTES
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                current_value = data.get('current_value', 0)
                max_predicted = current_value
                is_active = True  # Always active to respect minReplicaCount
                
                logger.info(f"IsActive check: max_predicted={max_predicted}, active={is_active}")
                
                return externalscaler_pb2.IsActiveResponse(result=is_active)
            else:
                logger.error(f"Forecaster returned status {response.status_code}")
                return externalscaler_pb2.IsActiveResponse(result=True)
                
        except Exception as e:
            logger.error(f"IsActive failed: {e}")
            return externalscaler_pb2.IsActiveResponse(result=True)
    
    def StreamIsActive(self, request, context):
        while True:
            try:
                response = requests.post(
                    f"{FORECASTER_URL}/forecast",
                    json={
                        "metric_name": METRIC_NAME,
                        "horizon_minutes": FORECAST_MINUTES
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    max_predicted = max(data.get('predicted_values', [0]))
                    is_active = max_predicted > TARGET_VALUE
                    
                    logger.info(f"StreamIsActive: max_predicted={max_predicted}, active={is_active}")
                    
                    yield externalscaler_pb2.IsActiveResponse(result=is_active)
                else:
                    yield externalscaler_pb2.IsActiveResponse(result=True)
                    
            except Exception as e:
                logger.error(f"StreamIsActive failed: {e}")
                yield externalscaler_pb2.IsActiveResponse(result=True)
            
            asyncio.sleep(10)  # Check every 10 seconds
    
    def GetMetricSpec(self, request, context):
        spec = externalscaler_pb2.GetMetricSpecResponse()
        spec.metric_specs.append(
            externalscaler_pb2.MetricSpec(
                metric_name="predicted_load",
                target_size=int(TARGET_VALUE)
            )
        )
        return spec
    
    def GetMetrics(self, request, context):
        try:
            response = requests.post(
                f"{FORECASTER_URL}/forecast",
                json={
                    "metric_name": METRIC_NAME,
                    "horizon_minutes": FORECAST_MINUTES
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Use current actual value instead of predictions for now
                current_value = data.get('current_value', 0)
                max_predicted = current_value
                
                # Calculate desired replicas based on predicted load
                desired_replicas = max(
                    MIN_REPLICAS,
                    min(MAX_REPLICAS, int(max_predicted / TARGET_VALUE) + 1)
                )
                
                # Report metric value that will result in desired replicas
                # HPA calculates: desired_replicas = metric_value / target_value
                # So: metric_value = desired_replicas * target_value
                metric_value = desired_replicas * TARGET_VALUE
                
                logger.info(
                    f"GetMetrics: predicted={max_predicted}, "
                    f"metric_value={metric_value}, desired_replicas={desired_replicas}"
                )
                
                return externalscaler_pb2.GetMetricsResponse(
                    metrics=[
                        externalscaler_pb2.MetricValue(
                            metric_name="predicted_load",
                            metric_value=int(metric_value)
                        )
                    ]
                )
            else:
                logger.error(f"Forecaster returned status {response.status_code}")
                # Return current target to maintain current scale
                return externalscaler_pb2.GetMetricsResponse(
                    metrics=[
                        externalscaler_pb2.MetricValue(
                            metric_name="predicted_load",
                            metric_value=int(TARGET_VALUE)
                        )
                    ]
                )
                
        except Exception as e:
            logger.error(f"GetMetrics failed: {e}")
            # Return safe default
            return externalscaler_pb2.GetMetricsResponse(
                metrics=[
                    externalscaler_pb2.MetricValue(
                        metric_name="predicted_load",
                        metric_value=int(TARGET_VALUE)
                    )
                ]
            )
    
    def StreamGetMetrics(self, request, context) -> Iterator[externalscaler_pb2.GetMetricsResponse]:
        while True:
            try:
                response = requests.post(
                    f"{FORECASTER_URL}/forecast",
                    json={
                        "metric_name": METRIC_NAME,
                        "horizon_minutes": FORECAST_MINUTES
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    predicted_values = data.get('predicted_values', [0])
                    max_predicted = max(predicted_values) if predicted_values else 0
                    
                    metric_value = max_predicted
                    
                    logger.info(f"StreamGetMetrics: metric_value={metric_value}")
                    
                    yield externalscaler_pb2.GetMetricsResponse(
                        metrics=[
                            externalscaler_pb2.MetricValue(
                                metric_name="predicted_load",
                                metric_value=int(metric_value)
                            )
                        ]
                    )
                else:
                    yield externalscaler_pb2.GetMetricsResponse(
                        metrics=[
                            externalscaler_pb2.MetricValue(
                                metric_name="predicted_load",
                                metric_value=int(TARGET_VALUE)
                            )
                        ]
                    )
                    
            except Exception as e:
                logger.error(f"StreamGetMetrics failed: {e}")
                yield externalscaler_pb2.GetMetricsResponse(
                    metrics=[
                        externalscaler_pb2.MetricValue(
                            metric_name="predicted_load",
                            metric_value=int(TARGET_VALUE)
                        )
                    ]
                )
            
            asyncio.sleep(30)  # Update every 30 seconds


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    externalscaler_pb2_grpc.add_ExternalScalerServicer_to_server(
        ExternalScaler(), server
    )
    
    port = os.getenv("GRPC_PORT", "6000")
    server.add_insecure_port(f"[::]:{port}")
    
    logger.info(f"KEDA External Scaler starting on port {port}")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
