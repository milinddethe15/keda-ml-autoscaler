import asyncio
import json
import random
import time
from datetime import datetime
from typing import List

import aiohttp
import websockets
from websockets.exceptions import WebSocketException

class LoadTester:
    def __init__(self, base_url: str, ws_url: str):
        self.base_url = base_url
        self.ws_url = ws_url
        self.active_connections = []
        self.message_count = 0
        self.start_time = time.time()
        
    async def create_client(self, client_id: str):
        try:
            websocket = await websockets.connect(f"{self.ws_url}/ws/{client_id}")
            self.active_connections.append(websocket)
            
            # Send messages periodically
            while True:
                message = {
                    "type": "message",
                    "message": f"Test message from {client_id} at {datetime.now().isoformat()}"
                }
                await websocket.send(json.dumps(message))
                self.message_count += 1
                
                # Random delay between messages
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
        except WebSocketException as e:
            print(f"Client {client_id} disconnected: {e}")
        except Exception as e:
            print(f"Error in client {client_id}: {e}")
    
    async def simulate_spike_pattern(self, base_clients: int = 10, spike_clients: int = 50):
        tasks = []
        
        # Start with base load
        print(f"Starting base load with {base_clients} clients...")
        for i in range(base_clients):
            task = asyncio.create_task(self.create_client(f"base_client_{i}"))
            tasks.append(task)
            await asyncio.sleep(0.1)
        
        # Wait for stabilization
        await asyncio.sleep(30)
        
        # Create traffic spike
        print(f"Creating traffic spike with {spike_clients} additional clients...")
        for i in range(spike_clients):
            task = asyncio.create_task(self.create_client(f"spike_client_{i}"))
            tasks.append(task)
            await asyncio.sleep(0.05)
        
        # Maintain spike
        await asyncio.sleep(60)
        
        # Gradual decrease
        print("Gradually decreasing load...")
        for task in tasks[base_clients:]:
            task.cancel()
            await asyncio.sleep(0.2)
        
        # Maintain base load
        await asyncio.sleep(30)
        
        # Cancel remaining tasks
        for task in tasks[:base_clients]:
            task.cancel()
    
    async def simulate_daily_pattern(self, duration_hours: float = 0.5):
        tasks = []
        duration_seconds = duration_hours * 3600
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # Simulate daily traffic pattern
            hour_equivalent = ((time.time() - start_time) / duration_seconds) * 24
            
            # Calculate target clients based on time of day pattern
            base_clients = 5
            if 6 <= hour_equivalent < 9:  # Morning spike
                target_clients = base_clients + int(20 * (hour_equivalent - 6) / 3)
            elif 9 <= hour_equivalent < 17:  # Daytime steady
                target_clients = base_clients + 20
            elif 17 <= hour_equivalent < 20:  # Evening spike
                target_clients = base_clients + 30
            elif 20 <= hour_equivalent < 22:  # Evening decline
                target_clients = base_clients + int(20 * (22 - hour_equivalent) / 2)
            else:  # Night time low
                target_clients = base_clients
            
            current_clients = len([t for t in tasks if not t.done()])
            
            if current_clients < target_clients:
                # Add clients
                for i in range(target_clients - current_clients):
                    client_id = f"client_{int(time.time() * 1000)}_{i}"
                    task = asyncio.create_task(self.create_client(client_id))
                    tasks.append(task)
                    await asyncio.sleep(0.1)
            elif current_clients > target_clients:
                # Remove clients
                active_tasks = [t for t in tasks if not t.done()]
                for task in active_tasks[:current_clients - target_clients]:
                    task.cancel()
            
            print(f"Time: {hour_equivalent:.1f}h, Clients: {current_clients}, Target: {target_clients}, Messages: {self.message_count}")
            await asyncio.sleep(5)
        
        # Cleanup
        for task in tasks:
            if not task.done():
                task.cancel()
    
    async def simulate_random_spikes(self, base_clients: int = 10, duration_minutes: int = 10):
        tasks = []
        duration_seconds = duration_minutes * 60
        start_time = time.time()
        
        # Start base load
        for i in range(base_clients):
            task = asyncio.create_task(self.create_client(f"base_{i}"))
            tasks.append(task)
            await asyncio.sleep(0.1)
        
        while time.time() - start_time < duration_seconds:
            # Random chance of spike
            if random.random() < 0.1:  # 10% chance every check
                spike_size = random.randint(10, 30)
                print(f"Random spike: Adding {spike_size} clients")
                
                spike_tasks = []
                for i in range(spike_size):
                    task = asyncio.create_task(self.create_client(f"spike_{time.time()}_{i}"))
                    tasks.append(task)
                    spike_tasks.append(task)
                    await asyncio.sleep(0.05)
                
                # Maintain spike for 30-60 seconds
                await asyncio.sleep(random.uniform(30, 60))
                
                # Remove spike
                for task in spike_tasks:
                    if not task.done():
                        task.cancel()
                print(f"Spike ended")
            
            await asyncio.sleep(10)
        
        # Cleanup
        for task in tasks:
            if not task.done():
                task.cancel()
    
    def print_stats(self):
        elapsed = time.time() - self.start_time
        rate = self.message_count / elapsed if elapsed > 0 else 0
        print(f"\nStats: Total messages: {self.message_count}, Rate: {rate:.2f} msg/s")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test the chat application")
    parser.add_argument("--host", default="localhost", help="Host to connect to")
    parser.add_argument("--port", default=8000, help="Port to connect to")
    parser.add_argument("--pattern", choices=["spike", "daily", "random"], default="spike",
                       help="Load pattern to simulate")
    parser.add_argument("--base-clients", type=int, default=10,
                       help="Number of base clients")
    parser.add_argument("--spike-clients", type=int, default=50,
                       help="Number of spike clients")
    parser.add_argument("--duration", type=float, default=10,
                       help="Duration in minutes")
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    ws_url = f"ws://{args.host}:{args.port}"
    
    tester = LoadTester(base_url, ws_url)
    
    try:
        if args.pattern == "spike":
            await tester.simulate_spike_pattern(args.base_clients, args.spike_clients)
        elif args.pattern == "daily":
            await tester.simulate_daily_pattern(args.duration / 60)  # Convert to hours
        elif args.pattern == "random":
            await tester.simulate_random_spikes(args.base_clients, args.duration)
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        tester.print_stats()


if __name__ == "__main__":
    asyncio.run(main())
