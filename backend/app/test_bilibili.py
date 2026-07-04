import asyncio
import logging
import sys
from services.download_engine import download_video

# Set up logging to stdout so we can see the exact output and attempts
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def test():
    url = "https://b23.tv/W2AcR1f"
    print(f"Starting test for URL: {url}")
    try:
        res = await download_video(url, output_dir="/app/data/downloads")
        print("\nSUCCESS!")
        print(f"Result: {res}")
    except Exception as e:
        print("\nFAILURE!")
        print(f"Error: {e}")
        if hasattr(e, "metadata"):
            print(f"Metadata: {e.metadata}")

if __name__ == "__main__":
    asyncio.run(test())
