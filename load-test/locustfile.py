import json
import random
import time
from locust import HttpUser, TaskSet, between, events, task
from websocket import create_connection, WebSocketTimeoutException


class ChatUser(HttpUser):
    wait_time = between(1, 3)
    ws = None
    user_id = None
    
    def on_start(self):
        self.user_id = f"user_{time.time()}_{random.randint(1000, 9999)}"
        self.connect_websocket()
    
    def on_stop(self):
        if self.ws:
            self.ws.close()
    
    def connect_websocket(self):
        try:
            ws_url = self.host.replace("http://", "ws://").replace("https://", "wss://")
            self.ws = create_connection(f"{ws_url}/ws/{self.user_id}", timeout=5)
            
            events.request.fire(
                request_type="WebSocket",
                name="connect",
                response_time=0,
                response_length=0,
                exception=None,
                context={}
            )
        except Exception as e:
            events.request.fire(
                request_type="WebSocket",
                name="connect",
                response_time=0,
                response_length=0,
                exception=e,
                context={}
            )
    
    @task(3)
    def send_message(self):
        if not self.ws:
            self.connect_websocket()
            return
        
        start_time = time.time()
        try:
            message = {
                "type": "message",
                "message": f"Hello from {self.user_id} at {time.time()}"
            }
            self.ws.send(json.dumps(message))
            
            # Try to receive response
            self.ws.settimeout(1)
            try:
                response = self.ws.recv()
                response_time = (time.time() - start_time) * 1000
                
                events.request.fire(
                    request_type="WebSocket",
                    name="send_message",
                    response_time=response_time,
                    response_length=len(response),
                    exception=None,
                    context={}
                )
            except WebSocketTimeoutException:
                # No response expected for broadcasts
                response_time = (time.time() - start_time) * 1000
                events.request.fire(
                    request_type="WebSocket",
                    name="send_message",
                    response_time=response_time,
                    response_length=0,
                    exception=None,
                    context={}
                )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="WebSocket",
                name="send_message",
                response_time=response_time,
                response_length=0,
                exception=e,
                context={}
            )
            # Reconnect on error
            self.ws = None
    
    @task(1)
    def check_stats(self):
        try:
            response = self.client.get("/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"Current stats: {stats}")
        except Exception as e:
            print(f"Failed to get stats: {e}")
    
    @task(1)
    def check_health(self):
        self.client.get("/health")
