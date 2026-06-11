import asyncio
import httpx
import os
from app.config.settings import settings

NVIDIA_KEY = settings.nvidia_api_key

async def test_llm():
    print("=== Testing NVIDIA LLM ===", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                json={"model": "meta/llama-3.3-70b-instruct",
                      "messages": [{"role": "user", "content": "Say hello"}],
                      "max_tokens": 10},
                headers={"Authorization": f"Bearer {NVIDIA_KEY}",
                         "Content-Type": "application/json"},
            )
            print(f"  LLM Status: {r.status_code}", flush=True)
            print(f"  LLM Body: {r.text[:400]}", flush=True)
    except Exception as e:
        print(f"  LLM ERROR: {type(e).__name__}: {e}", flush=True)

asyncio.run(test_llm())
