"""
WebSocket server to integrate with Alice.

- Broadcasts selected EventBus events to connected WS clients.
- Receives messages from clients and forwards them to `alice.respond(...)`.

Usage:
    from Transport.ws_server import start_ws_server
    server = await start_ws_server(alice, host='0.0.0.0', port=8765)

Requires `websockets` package: `pip install websockets`
"""
from __future__ import annotations
import asyncio
import json
from typing import Any, Set

import websockets

from loguru import logger
from DataClass.ChatMessage import ChatMessage
from EventBus import EventBus
from DataClass.EventType import EventType


_connected: Set[Any] = set()


async def _client_handler(ws, alice):
    """Handle a single client connection: receive messages and send responses.
    Expect client to send JSON objects like: {"type":"user_input","content": "..."}
    """
    logger.debug(f"WS client connected: {ws.remote_address}")
    _connected.add(ws)
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except Exception:
                logger.warning("Received non-JSON from WS client")
                continue

            # Simple protocol: type=user_input -> forward to alice.respond
            msg_type = data.get("type")
            if msg_type == "user_input":
                content = data.get("content", "")
                # Build a ChatMessage-like dict for Alice
                user_inputs = {"text": content}
                try:
                    # call alice.respond asynchronously
                    resp = await alice.respond(user_inputs)
                except Exception as e:
                    logger.exception(f"alice.respond failed: {e}")
                    resp = ""

                # return response to client
                # await ws.send(json.dumps({"type": "assistant_response", "content": resp}, ensure_ascii=False))
            else:
                # unknown type: echo
                await ws.send(json.dumps({"type": "error", "message": "unknown type"}))
    except websockets.exceptions.ConnectionClosed:
        logger.debug(f"WS client disconnected: {ws.remote_address}")
    finally:
        _connected.discard(ws)


def _json_default(obj: Any):
    # Best-effort conversion for event payloads (ChatMessage, dataclasses, etc.)
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        return obj.to_dict()
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def _eventbus_subscriber_factory():
    # IMPORTANT: return an async subscriber so EventBus dispatches it in the running loop.
    async def _subscriber(event):
        await _broadcast_event(event)

    return _subscriber


async def _broadcast_event(event):
    if not _connected:
        return
    payload = {
        "type": "event",
        "event_type": event.event_type,
        "turn_id": event.turn_id,
        "timestamp": event.timestamp,
        "data": event.data,
    }
    text = json.dumps(payload, ensure_ascii=False, default=_json_default)

    to_remove = []
    for ws in list(_connected):
        try:
            await ws.send(text)
        except Exception:
            to_remove.append(ws)
    for ws in to_remove:
        _connected.discard(ws)


async def start_ws_server(alice, host: str = "0.0.0.0", port: int = 8765):
    """Start the websocket server and subscribe to Alice's EventBus.

    Returns the `websockets` server object.
    """
    # subscribe to Alice's event bus
    if hasattr(alice, "event_bus") and isinstance(alice.event_bus, EventBus):
        # subscribe to events using EventType constants
        alice.event_bus.subscribe(EventType.POST_HANDLE_COMPLETED, _eventbus_subscriber_factory())

    # Define a handler that matches the expected signature for websockets >=11.0
    async def ws_handler(ws):
        await _client_handler(ws, alice)

    server = await websockets.serve(ws_handler, host, port)
    logger.info(f"WebSocket server started on {host}:{port}")
    return server


async def stop_ws_server(server):
    server.close()
    await server.wait_closed()
    logger.info("WebSocket server stopped")
