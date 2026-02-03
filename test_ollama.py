import httpx
import asyncio

async def check():
    url = "http://localhost:11434/api/tags"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=2.0)
            print(f"Ollama Status: {response.status_code}")
            print(f"Models: {response.json()}")
    except Exception as e:
        print(f"Ollama not reachable: {e}")

if __name__ == "__main__":
    asyncio.run(check())
