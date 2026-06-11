"""Quick diagnostic: test NVIDIA LLM + FLUX + Pollinations independently."""
import asyncio
import httpx
import base64
import sys
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

async def test_flux():
    print("\n=== Testing NVIDIA FLUX ===", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell",
                json={"prompt": "A red ball", "width": 1024, "height": 1024, "steps": 4, "seed": 42},
                headers={"Authorization": f"Bearer {NVIDIA_KEY}",
                         "Accept": "application/json",
                         "Content-Type": "application/json"},
            )
            print(f"  FLUX Status: {r.status_code}", flush=True)
            if r.status_code == 200:
                data = r.json()
                arts = data.get("artifacts", [])
                if arts and "base64" in arts[0]:
                    print(f"  FLUX Image: {len(base64.b64decode(arts[0]['base64'])):,} bytes OK", flush=True)
                else:
                    print(f"  FLUX unexpected keys: {list(data.keys())}", flush=True)
            else:
                print(f"  FLUX Error: {r.text[:400]}", flush=True)
    except Exception as e:
        print(f"  FLUX ERROR: {type(e).__name__}: {e}", flush=True)

async def test_pollinations():
    print("\n=== Testing Pollinations ===", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
            r = await c.get(
                "https://image.pollinations.ai/prompt/a%20red%20ball?width=1024&height=1024&nologo=true&seed=1"
            )
            print(f"  Poll Status: {r.status_code}", flush=True)
            if r.status_code == 200:
                print(f"  Poll Image: {len(r.content):,} bytes OK", flush=True)
            else:
                print(f"  Poll Error: {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"  Poll ERROR: {type(e).__name__}: {e}", flush=True)

async def main():
    # Run each independently so one failure doesn't block others
    await test_llm()
    await test_flux()
    await test_pollinations()
    print("\n=== DONE ===", flush=True)

asyncio.run(main())
