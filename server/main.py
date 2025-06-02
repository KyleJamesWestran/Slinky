### --- Part 1: Web Server (hosted on Render) ---
# File: server/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio

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
            # If there's a pending future waiting for a response, set its result
            future = pending_results.get(client_id)
            if future and not future.done():
                future.set_result(msg)
    except WebSocketDisconnect:
        del connected_clients[client_id]
        # Cancel any pending future to avoid hanging
        future = pending_results.get(client_id)
        if future and not future.done():
            future.set_exception(WebSocketDisconnect())

@app.post("/run_sql/{client_id}")
async def run_sql(client_id: str, query: str):
    if client_id not in connected_clients:
        return JSONResponse(content={"error": "Client not connected"}, status_code=404)

    # Create a Future to wait for the agent's reply
    future = asyncio.get_event_loop().create_future()
    pending_results[client_id] = future

    await connected_clients[client_id].send_text(query)

    try:
        # Wait max 10 seconds for the response
        result = await asyncio.wait_for(future, timeout=10)
    except asyncio.TimeoutError:
        del pending_results[client_id]
        return JSONResponse(content={"error": "Timeout waiting for agent response"}, status_code=504)

    del pending_results[client_id]
    return {"result": result}


# Run locally: uvicorn main:app --reload