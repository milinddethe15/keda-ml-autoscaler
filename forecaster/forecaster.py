import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import redis
from fastapi import FastAPI, HTTPException
from prometheus_client import generate_latest
from prophet import Prophet
from pydantic import BaseModel
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Load Forecaster")

# Configuration
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
FORECAST_HORIZON_MINUTES = int(os.getenv("FORECAST_HORIZON_MINUTES", "10"))
HISTORY_HOURS = int(os.getenv("HISTORY_HOURS", "24"))
MIN_TRAINING_POINTS = 10

redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)


class ForecastRequest(BaseModel):
    metric_name: str = "chat_messages_per_second"
    horizon_minutes: int = FORECAST_HORIZON_MINUTES


class ForecastResponse(BaseModel):
    current_value: float
    predicted_values: List[float]
    timestamps: List[str]
    confidence_lower: List[float]
    confidence_upper: List[float]


class LoadForecaster:
    def __init__(self):
        self.model = None
        self.last_training_time = None
        self.training_interval_minutes = 10
        self.scaler = StandardScaler()

    async def get_current_value(self, metric_name: str) -> float:
        """Get current aggregated value across all pods"""
        import aiohttp
        
        # Use sum() to aggregate across all pods
        query = f'sum({metric_name})'
        url = f"{PROMETHEUS_URL}/api/v1/query"
        
        params = {'query': query}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    logger.info(f"Prometheus query: {query}, status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        result = data.get('data', {}).get('result', [])
                        logger.info(f"Prometheus result: {result}")
                        if result and len(result) > 0:
                            value = float(result[0]['value'][1])
                            logger.info(f"Current value: {value}")
                            return value
        except Exception as e:
            logger.error(f"Failed to fetch current value: {e}")
        
        logger.warning(f"No current value found, returning 0.0")
        return 0.0

    async def fetch_prometheus_metrics(self, metric_name: str) -> pd.DataFrame:
        import aiohttp
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=HISTORY_HOURS)
        
        query = f'{metric_name}[{HISTORY_HOURS}h]'
        url = f"{PROMETHEUS_URL}/api/v1/query"
        
        params = {
            'query': query,
            'time': end_time.timestamp()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_prometheus_response(data)
        except Exception as e:
            logger.error(f"Failed to fetch Prometheus metrics: {e}")
        
        # Fallback to synthetic data for demo
        return self._generate_synthetic_data()

    def _parse_prometheus_response(self, response: dict) -> pd.DataFrame:
        if response.get('status') != 'success':
            return self._generate_synthetic_data()
        
        data = response.get('data', {})
        result = data.get('result', [])
        
        if not result:
            return self._generate_synthetic_data()
        
        timestamps = []
        values = []
        
        for item in result[0].get('values', []):
            timestamps.append(datetime.fromtimestamp(float(item[0])))
            values.append(float(item[1]))
        
        if len(timestamps) < MIN_TRAINING_POINTS:
            return self._generate_synthetic_data()
        
        return pd.DataFrame({'ds': timestamps, 'y': values})

    def _generate_synthetic_data(self) -> pd.DataFrame:
        now = datetime.utcnow()
        timestamps = []
        values = []
        
        for i in range(HISTORY_HOURS * 60):  # One point per minute
            ts = now - timedelta(minutes=i)
            timestamps.append(ts)
            
            # Synthetic pattern: daily cycle with random noise
            hour = ts.hour
            base_load = 50
            daily_pattern = 30 * np.sin(2 * np.pi * hour / 24 - np.pi/2) + base_load
            spike_probability = 0.05
            
            if np.random.random() < spike_probability:
                value = daily_pattern + np.random.uniform(20, 50)
            else:
                value = daily_pattern + np.random.normal(0, 5)
            
            values.append(max(0, value))
        
        df = pd.DataFrame({'ds': timestamps[::-1], 'y': values[::-1]})
        return df

    def train_model(self, data: pd.DataFrame):
        model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            holidays_prior_scale=10.0,
            seasonality_mode='multiplicative',
            interval_width=0.95,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False
        )
        
        model.fit(data)
        self.model = model
        self.last_training_time = datetime.utcnow()
        
        # Store model metadata in Redis
        redis_client.set(
            "forecaster:last_training",
            self.last_training_time.isoformat()
        )
        
        logger.info(f"Model trained with {len(data)} data points")

    def predict(self, horizon_minutes: int) -> Dict:
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        future = self.model.make_future_dataframe(periods=horizon_minutes, freq='min')
        forecast = self.model.predict(future)
        
        # Get predictions for the future horizon
        future_forecast = forecast.tail(horizon_minutes)
        
        return {
            'timestamps': future_forecast['ds'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'predicted_values': future_forecast['yhat'].tolist(),
            'confidence_lower': future_forecast['yhat_lower'].tolist(),
            'confidence_upper': future_forecast['yhat_upper'].tolist()
        }

    async def get_forecast(self, metric_name: str, horizon_minutes: int) -> ForecastResponse:
        # Check if model needs retraining
        should_retrain = (
            self.model is None or 
            self.last_training_time is None or
            (datetime.utcnow() - self.last_training_time).total_seconds() > self.training_interval_minutes * 60
        )
        
        if should_retrain:
            data = await self.fetch_prometheus_metrics(metric_name)
            if len(data) >= MIN_TRAINING_POINTS:
                self.train_model(data)
            else:
                logger.warning(f"Insufficient data points: {len(data)}")
                data = self._generate_synthetic_data()
                self.train_model(data)
        
        # Get current value from live metrics
        current_value = await self.get_current_value(metric_name)
        
        # Make predictions
        predictions = self.predict(horizon_minutes)
        
        return ForecastResponse(
            current_value=current_value,
            predicted_values=predictions['predicted_values'],
            timestamps=predictions['timestamps'],
            confidence_lower=predictions['confidence_lower'],
            confidence_upper=predictions['confidence_upper']
        )


forecaster = LoadForecaster()


@app.get("/")
async def root():
    return {"service": "forecaster", "status": "running"}


@app.get("/health")
async def health():
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected",
            "model_trained": forecaster.model is not None
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503


@app.post("/forecast", response_model=ForecastResponse)
async def get_forecast(request: ForecastRequest):
    try:
        return await forecaster.get_forecast(
            request.metric_name,
            request.horizon_minutes
        )
    except Exception as e:
        logger.error(f"Forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
