import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Set

import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

app = FastAPI(title="Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis_client = redis.Redis(
    host="redis", port=6379, decode_responses=True, socket_connect_timeout=5
)

# Prometheus metrics
messages_total = Counter("chat_messages_total", "Total number of messages processed")
active_connections_gauge = Gauge(
    "chat_active_connections", "Number of active WebSocket connections"
)
message_latency = Histogram(
    "chat_message_latency_seconds", "Message processing latency"
)
messages_per_second = Gauge("chat_messages_per_second", "Messages per second rate")

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.message_rates: list = []
        self.rate_window = 60  # seconds
        
    def update_message_rate(self):
        """Update message rate by cleaning up old timestamps"""
        current_time = time.time()
        self.message_rates = [
            t for t in self.message_rates if t > current_time - self.rate_window
        ]
        messages_per_second.set(len(self.message_rates) / self.rate_window)

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        active_connections_gauge.set(len(self.active_connections))

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            active_connections_gauge.set(len(self.active_connections))

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str, sender_id: str):
        start_time = time.time()
        
        # Update message rate
        self.message_rates.append(time.time())
        self.update_message_rate()
        
        # Store in Redis
        await redis_client.lpush(
            "chat_messages",
            json.dumps(
                {
                    "sender": sender_id,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        )
        await redis_client.ltrim("chat_messages", 0, 999)  # Keep last 1000 messages
        
        # Broadcast to all connections
        tasks = []
        for client_id, connection in self.active_connections.items():
            if client_id != sender_id:
                message_data = json.dumps(
                    {"sender": sender_id, "message": message, "type": "broadcast"}
                )
                tasks.append(connection.send_text(message_data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update metrics
        messages_total.inc()
        message_latency.observe(time.time() - start_time)


manager = ConnectionManager()

# Background task to update message rate
async def update_metrics_task():
    """Background task to periodically update metrics"""
    while True:
        await asyncio.sleep(5)  # Update every 5 seconds
        manager.update_message_rate()

# Start background task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_metrics_task())


@app.get("/")
async def root():
    return {"service": "chat", "status": "running"}


@app.get("/health")
async def health():
    try:
        await redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    try:
        await manager.broadcast(f"{client_id} joined the chat", client_id)
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                if message_data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                else:
                    await manager.broadcast(message_data.get("message", ""), client_id)
            except json.JSONDecodeError:
                await manager.broadcast(data, client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"{client_id} left the chat", "system")


@app.get("/stats")
async def get_stats():
    return {
        "active_connections": len(manager.active_connections),
        "messages_per_second": messages_per_second._value.get(),
        "total_messages": messages_total._value.get(),
    }


@app.post("/api/message")
async def send_message_http(message_data: dict):
    """HTTP endpoint to send messages - distributes load evenly across pods"""
    start_time = time.time()
    
    sender_id = message_data.get("sender", "http_client")
    message = message_data.get("message", "")
    
    # Update message rate (same as WebSocket)
    manager.message_rates.append(time.time())
    manager.update_message_rate()
    
    # Store in Redis (same as WebSocket)
    await redis_client.lpush(
        "chat_messages",
        json.dumps(
            {
                "sender": sender_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
    )
    await redis_client.ltrim("chat_messages", 0, 999)  # Keep last 1000 messages
    
    # Update metrics (same as WebSocket)
    messages_total.inc()
    message_latency.observe(time.time() - start_time)
    
    return {
        "status": "success",
        "sender": sender_id,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
