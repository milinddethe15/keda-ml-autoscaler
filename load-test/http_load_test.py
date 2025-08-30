#!/usr/bin/env python3
"""
HTTP-based load test for chat backend - distributes load evenly across pods
"""

import asyncio
import aiohttp
import argparse
import json
import time
from datetime import datetime


class HTTPLoadTester:
    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"
        self.session = None
        self.message_count = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_message(self, sender_id: str, message: str):
        """Send a single HTTP message"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/message",
                json={"sender": sender_id, "message": message},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    self.message_count += 1
                    return True
                else:
                    print(f"Error: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"Request failed: {e}")
            return False
    
    async def get_stats(self):
        """Get current backend statistics"""
        try:
            async with self.session.get(f"{self.base_url}/stats") as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"Stats request failed: {e}")
        return None
    
    async def worker(self, worker_id: int, messages_per_second: float, duration: int):
        """Worker that sends messages at specified rate"""
        interval = 1.0 / messages_per_second if messages_per_second > 0 else 1.0
        end_time = time.time() + duration
        
        print(f"Worker {worker_id} starting: {messages_per_second} msg/sec for {duration}s")
        
        while time.time() < end_time:
            start = time.time()
            
            message = f"HTTP message from worker-{worker_id} at {datetime.now().strftime('%H:%M:%S')}"
            await self.send_message(f"worker-{worker_id}", message)
            
            # Sleep to maintain rate
            elapsed = time.time() - start
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        print(f"Worker {worker_id} completed: sent {self.message_count} messages")


async def run_load_test(host: str, port: int, pattern: str, duration: int = 60):
    """Run different load test patterns"""
    
    async with HTTPLoadTester(host, port) as tester:
        print(f"Starting HTTP load test: {pattern} pattern for {duration}s")
        print(f"Target: {host}:{port}")
        
        # Get initial stats
        initial_stats = await tester.get_stats()
        if initial_stats:
            print(f"Initial stats: {initial_stats}")
        
        if pattern == "spike":
            # Sudden spike: 0 -> 20 msg/sec -> 0
            print("\n=== SPIKE PATTERN ===")
            print("Phase 1: Baseline (5s)")
            await asyncio.sleep(5)
            
            print("Phase 2: Spike to 20 msg/sec (30s)")
            workers = []
            for i in range(4):  # 4 workers, 5 msg/sec each = 20 total
                workers.append(asyncio.create_task(
                    tester.worker(i, 5.0, 30)
                ))
            await asyncio.gather(*workers)
            
            print("Phase 3: Cool down (25s)")
            await asyncio.sleep(25)
            
        elif pattern == "gradual":
            # Gradual increase: 0 -> 2 -> 5 -> 10 -> 15 -> 5 -> 0
            phases = [
                (2, 10),   # 2 msg/sec for 10s
                (5, 10),   # 5 msg/sec for 10s  
                (10, 15),  # 10 msg/sec for 15s
                (15, 15),  # 15 msg/sec for 15s
                (5, 10),   # 5 msg/sec for 10s
            ]
            
            print("\n=== GRADUAL PATTERN ===")
            for i, (rate, duration_phase) in enumerate(phases):
                print(f"Phase {i+1}: {rate} msg/sec for {duration_phase}s")
                
                # Calculate workers needed
                workers_needed = min(rate, 10)  # Max 10 workers
                rate_per_worker = rate / workers_needed
                
                workers = []
                for worker_id in range(workers_needed):
                    workers.append(asyncio.create_task(
                        tester.worker(worker_id, rate_per_worker, duration_phase)
                    ))
                await asyncio.gather(*workers)
                
                # Brief pause between phases
                await asyncio.sleep(2)
        
        elif pattern == "sustained":
            # Sustained high load
            print(f"\n=== SUSTAINED PATTERN: 12 msg/sec for {duration}s ===")
            workers = []
            for i in range(6):  # 6 workers, 2 msg/sec each = 12 total
                workers.append(asyncio.create_task(
                    tester.worker(i, 2.0, duration)
                ))
            await asyncio.gather(*workers)
        
        # Get final stats
        await asyncio.sleep(2)
        final_stats = await tester.get_stats()
        if final_stats:
            print(f"\nFinal stats: {final_stats}")
            if initial_stats:
                messages_sent = final_stats['total_messages'] - initial_stats['total_messages']
                print(f"Messages sent during test: {messages_sent}")


async def main():
    parser = argparse.ArgumentParser(description="HTTP Load Tester for Chat Backend")
    parser.add_argument("--host", default="localhost", help="Backend host")
    parser.add_argument("--port", type=int, default=8000, help="Backend port")
    parser.add_argument("--pattern", choices=["spike", "gradual", "sustained"], 
                       default="spike", help="Load test pattern")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Test duration in seconds (for sustained pattern)")
    
    args = parser.parse_args()
    
    print("🚀 HTTP Load Tester for KEDA ML Autoscaler")
    print("=" * 50)
    
    try:
        await run_load_test(args.host, args.port, args.pattern, args.duration)
        print("\n✅ Load test completed!")
    except KeyboardInterrupt:
        print("\n⏹️  Load test interrupted by user")
    except Exception as e:
        print(f"\n❌ Load test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
