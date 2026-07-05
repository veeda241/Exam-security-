#!/usr/bin/env python3
"""Simple WS load test helper — target ~200 concurrent subscribe messages."""
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("pip install websockets")
    sys.exit(1)


async def one_client(session_id: str, url: str):
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"type": "subscribe", "session_id": session_id}))
        await asyncio.sleep(2)
        await ws.send(json.dumps({"type": "ping"}))
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        return msg


async def main(concurrency: int = 50, url: str = "ws://localhost:8000/api/v1/ws"):
    tasks = [one_client(f"load-test-{i}", url) for i in range(concurrency)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = sum(1 for r in results if not isinstance(r, Exception))
    print(f"Completed {ok}/{concurrency} connections")
    return ok == concurrency


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(main(n))
