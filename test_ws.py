import asyncio
import os
import websockets
import json

# Usage: set DISPATCH_TOKEN to a JWT from /auth/login, then run this script.
TOKEN = os.environ["DISPATCH_TOKEN"]

async def test_ws():
    uri = f"ws://localhost:8002/ws/dispatch?token={TOKEN}"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            print(f"Response: {response}")
            await asyncio.sleep(5)
            print("Closing...")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_ws())
