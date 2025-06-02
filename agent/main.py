### --- Part 2: DropPoint Agent (local machine) ---
# File: agent/main.py

import os
from dotenv import load_dotenv
import asyncio
import websockets
import ssl
import sqlite3

# Load environment variables from .env file
load_dotenv()

AGENT_ID = os.getenv("AGENT_ID")

SERVER = os.getenv("SERVER")
SERVER_URL = f"{SERVER}/ws/{AGENT_ID}"

# ssl_context = ssl.create_default_context()
ssl_context = None  # Disable SSL for local testing; use proper certs in production

async def run_agent():
    async with websockets.connect(SERVER_URL, ssl=ssl_context) as websocket:
        while True:
            query = await websocket.recv()
            print("Received SQL query:", query)

            try:
                # Simple SQLite example - replace with your DB logic
                conn = sqlite3.connect("local.db")
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchall()
                conn.commit()
                conn.close()

                await websocket.send(str(result))
            except Exception as e:
                await websocket.send(f"ERROR: {str(e)}")

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(run_agent())
        except Exception as e:
            print("Disconnected, retrying in 5 seconds...", str(e))
            asyncio.run(asyncio.sleep(5))