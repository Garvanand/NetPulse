import asyncio
import httpx
import time
import statistics
import argparse
import json

async def fetch_endpoint(client, url, results):
    start = time.perf_counter()
    try:
        response = await client.get(url)
        response.raise_for_status()
        latency = (time.perf_counter() - start) * 1000
        results.append(latency)
    except Exception as e:
        # Ignore errors for latency calculation, or record them
        pass

async def load_test(url: str, concurrency: int, total_requests: int):
    results = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for _ in range(total_requests):
            tasks.append(fetch_endpoint(client, url, results))
            
            if len(tasks) >= concurrency:
                await asyncio.gather(*tasks)
                tasks = []
                
        if tasks:
            await asyncio.gather(*tasks)
            
    if not results:
        print(f"[{url}] All requests failed.")
        return
        
    results.sort()
    avg = statistics.mean(results)
    p50 = results[int(len(results) * 0.5)]
    p95 = results[int(len(results) * 0.95)]
    p99 = results[int(len(results) * 0.99)]
    
    print(f"\n--- Load Test Results for {url} ---")
    print(f"Total Requests: {len(results)} (Concurrency: {concurrency})")
    print(f"Average Latency: {avg:.2f} ms")
    print(f"p50 Latency:     {p50:.2f} ms")
    print(f"p95 Latency:     {p95:.2f} ms")
    print(f"p99 Latency:     {p99:.2f} ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/api/topology/graph")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()
    
    print(f"Starting load test on {args.url} with {args.concurrency} concurrent workers...")
    asyncio.run(load_test(args.url, args.concurrency, args.requests))
