from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio
from enum import Enum
from pydantic import BaseModel
import json

app = FastAPI()

connected_clients = {}  # client_id -> websocket
pending_results = {}    # client_id -> asyncio.Future

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    connected_clients[client_id] = websocket
    try:
        while True:
            msg = await websocket.receive_text()
            future = pending_results.get(client_id)
            if future and not future.done():
                future.set_result(msg)
    except WebSocketDisconnect:
        del connected_clients[client_id]
        future = pending_results.get(client_id)
        if future and not future.done():
            future.set_exception(WebSocketDisconnect())

# --- Updated Section ---

class CommandRequest(BaseModel):
    gui: str             # New: GUI identifier
    command: str         # Raw SQL or file path

@app.post("/run_command/{client_id}")
async def run_command(client_id: str, request: CommandRequest):
    if client_id not in connected_clients:
        return JSONResponse(content={"error": "Client not connected"}, status_code=404)

    future = asyncio.get_event_loop().create_future()
    pending_results[client_id] = future

    # New message format for updated agent
    message = {
        "gui": request.gui,
        "command": request.command
    }

    await connected_clients[client_id].send_text(json.dumps(message))

    try:
        result = await asyncio.wait_for(future, timeout=10)
    except asyncio.TimeoutError:
        del pending_results[client_id]
        return JSONResponse(content={"error": "Timeout waiting for agent response"}, status_code=504)

    del pending_results[client_id]
    return {"result": result}
