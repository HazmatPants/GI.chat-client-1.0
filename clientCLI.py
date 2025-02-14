import asyncio
import websockets
import json

host="localhost"
port=8765

username="test92"

async def chat():
    uri = f"ws://{host}:{port}"
    async with websockets.connect(uri) as websocket:
        print("Connected to the server! Type messages and press Enter to send.")
        
        async def send_messages():
            while True:
                message = input("You: ")
                message_data = {
                    "username": username,
                    "message": message
                    }
                message_json = json.dumps(message_data)
                await websocket.send(message_json)

        async def receive_messages():
            async for message in websocket:
                print(f"\nReceived: {message}")

        await asyncio.gather(send_messages(), receive_messages())

asyncio.run(chat())
