import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8002/ws/dispatch?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkaXNwYXRjaGVyMSIsInJvbGUiOiJtYW5hZ2VyIiwiZXhwIjoxNzcwNzczODg1fQ.dHJYeO77iv7KO7vLVdCHKxVyjHRcnI-w-I-A_GK0_XY"
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

