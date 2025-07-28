import os
import asyncio
import websockets
import json
import pyodbc
import sqlite3  # Optional, if you still want SQLite support
from agent_config_manager import load_config
import ssl


CONFIG_FILE = "config.json"

config = load_config()
AGENT_ID = config["client_guid"]
SERVER = config["client_server"]
SERVER_URL = f"{SERVER}/ws/{AGENT_ID}"
ssl_context = ssl.create_default_context()

def get_connection_info(guid):
    for conn in config["connections"]:
        if conn["connection_guid"] == guid:
            if "connection_type" not in conn:
                return {"error": "ERROR: 'connection_type'"}
            return conn
    return {"error": "ERROR: connection_guid not found"}

async def handle_command(data):
    try:
        guid = data.get("guid")
        command = data.get("command")

        if not guid or not command:
            return "ERROR: 'guid' or 'command' missing in request"

        conn_info = get_connection_info(guid)
        connection_type = conn_info.get("connection_type")

        if connection_type == "mssql":
            conn = pyodbc.connect(conn_info["connection_string"])
            cursor = conn.cursor()
            cursor.execute(command)
            result = cursor.fetchall()
            conn.commit()
            conn.close()
            return [tuple(row) for row in result]

        elif connection_type == "sqlite":
            connection_database_name = conn_info.get("connection_database_name")
            if not connection_database_name:
                return "ERROR: 'file_path' not specified for sqlite"
            conn = sqlite3.connect(connection_database_name)
            cursor = conn.cursor()
            cursor.execute(command)
            result = cursor.fetchall()
            conn.commit()
            conn.close()
            return result

        else:
            return f"ERROR: Unsupported connection_type: {connection_type}"

    except Exception as e:
        return f"ERROR: {str(e)}"

async def run_agent():
    print(f"Connecting to {SERVER_URL}")
    async with websockets.connect(SERVER_URL, ssl=ssl_context) as websocket:
        print("Service started")
        while True:
            raw = await websocket.recv()
            try:
                data = json.loads(raw)
                result = await handle_command(data)
            except json.JSONDecodeError:
                result = "ERROR: Invalid command format"
            await websocket.send(str(result))

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(run_agent())
        except Exception as e:
            print("Disconnected, retrying in 5 seconds...", str(e))
            asyncio.run(asyncio.sleep(5))
