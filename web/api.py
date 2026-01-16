"""Matrix Watcher Web API - FastAPI backend with WebSocket support."""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Matrix Watcher API", version="1.0.0")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
connected_clients: list[WebSocket] = []

# Event queues for real-time updates
predictions_queue: asyncio.Queue = asyncio.Queue()
levels_queue: asyncio.Queue = asyncio.Queue()


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


def load_recent_anomalies(hours: int = 24) -> list[dict]:
    """Load recent anomalies from logs."""
    anomalies = []
    logs_path = Path("logs/anomalies")
    
    if not logs_path.exists():
        return anomalies
    
    cutoff = time.time() - (hours * 3600)
    
    # Get recent log files
    for log_file in sorted(logs_path.glob("*.jsonl"), reverse=True)[:3]:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get("timestamp", 0) > cutoff:
                            anomalies.append(data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading {log_file}: {e}")
    
    # Sort by timestamp descending
    anomalies.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return anomalies[:50]  # Last 50


def load_patterns() -> dict:
    """Load pattern statistics."""
    patterns_file = Path("logs/patterns/patterns.json")
    
    if not patterns_file.exists():
        return {}
    
    try:
        with open(patterns_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading patterns: {e}")
        return {}


def get_active_predictions() -> list[dict]:
    """Get active predictions from recent conditions."""
    predictions = []
    patterns = load_patterns()
    
    # Crypto event types we care about
    crypto_events = {
        "btc_pump_1h", "btc_dump_1h", "btc_pump_4h", "btc_dump_4h",
        "btc_pump_24h", "btc_dump_24h", "eth_pump_1h", "eth_dump_1h",
        "eth_pump_4h", "eth_dump_4h", "eth_pump_24h", "eth_dump_24h",
        "btc_volatility_high", "btc_volatility_medium", "blockchain_anomaly"
    }
    
    for condition_key, events in patterns.items():
        for event_type, pattern in events.items():
            if event_type not in crypto_events:
                continue
            
            if pattern["condition_count"] >= 5 and pattern["actual_probability"] >= 0.4:
                avg_hours = pattern["avg_time_to_event"] / 3600 if pattern["avg_time_to_event"] > 0 else 0
                
                # Determine icon and color
                if "pump" in event_type:
                    icon = "📈"
                    color = "#00ff88"
                elif "dump" in event_type:
                    icon = "📉"
                    color = "#ff4444"
                elif "volatility" in event_type:
                    icon = "⚡"
                    color = "#ffaa00"
                else:
                    icon = "⛓️"
                    color = "#8888ff"
                
                # Format description
                desc = event_type.replace("_", " ").upper()
                if "btc" in event_type.lower():
                    desc = desc.replace("BTC", "BTC")
                if "eth" in event_type.lower():
                    desc = desc.replace("ETH", "ETH")
                
                predictions.append({
                    "id": f"{condition_key}_{event_type}",
                    "condition": condition_key,
                    "event": event_type,
                    "description": desc,
                    "probability": round(pattern["actual_probability"] * 100),
                    "avg_time_hours": round(avg_hours, 1),
                    "observations": pattern["condition_count"],
                    "occurrences": pattern["event_after_count"],
                    "icon": icon,
                    "color": color,
                    "timestamp": time.time()
                })
    
    # Sort by probability
    predictions.sort(key=lambda x: -x["probability"])
    return predictions[:20]  # Top 20


def format_level_event(anomaly: dict) -> dict | None:
    """Format anomaly for level display."""
    cluster = anomaly.get("cluster", {})
    index_data = anomaly.get("index", {})
    
    level = cluster.get("level", 0)
    if level < 1:
        return None
    
    timestamp = anomaly.get("timestamp", time.time())
    sources = list(set(a.get("sensor_source", "unknown") for a in cluster.get("anomalies", [])))
    
    # Color based on level
    colors = {
        1: "#666666",
        2: "#ffaa00",
        3: "#ff6600",
        4: "#ff3333",
        5: "#ff0000"
    }
    
    return {
        "id": f"level_{timestamp}",
        "level": level,
        "sources": sources,
        "sources_str": " + ".join(sources),
        "index": round(index_data.get("value", 0), 1),
        "status": index_data.get("status", "normal"),
        "timestamp": timestamp,
        "time_str": datetime.fromtimestamp(timestamp).strftime("%H:%M"),
        "color": colors.get(level, "#ffffff")
    }


@app.get("/")
async def root():
    """Serve PWA."""
    return FileResponse("web/static/index.html")


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/predictions")
async def get_predictions():
    """Get active predictions."""
    return {"predictions": get_active_predictions()}


@app.get("/api/levels")
async def get_levels():
    """Get recent level events."""
    anomalies = load_recent_anomalies(24)
    levels = []
    
    for a in anomalies:
        formatted = format_level_event(a)
        if formatted:
            levels.append(formatted)
    
    return {"levels": levels[:30]}


@app.get("/api/stats")
async def get_stats():
    """Get system statistics."""
    patterns = load_patterns()
    
    total_patterns = 0
    crypto_patterns = 0
    
    for cond_key, events in patterns.items():
        for event_type, pattern in events.items():
            if pattern["condition_count"] >= 5:
                total_patterns += 1
                if any(x in event_type for x in ["btc", "eth", "blockchain"]):
                    crypto_patterns += 1
    
    return {
        "total_patterns": total_patterns,
        "crypto_patterns": crypto_patterns,
        "pattern_groups": len(patterns),
        "timestamp": time.time()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial data
        await websocket.send_json({
            "type": "init",
            "predictions": get_active_predictions(),
            "levels": [format_level_event(a) for a in load_recent_anomalies(24) if format_level_event(a)][:30]
        })
        
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data == "refresh":
                    await websocket.send_json({
                        "type": "refresh",
                        "predictions": get_active_predictions(),
                        "levels": [format_level_event(a) for a in load_recent_anomalies(24) if format_level_event(a)][:30]
                    })
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Broadcast function for main.py to call
async def broadcast_prediction(prediction: dict):
    """Broadcast new prediction to all clients."""
    await manager.broadcast({
        "type": "prediction",
        "data": prediction
    })


async def broadcast_level(level: dict):
    """Broadcast new level event to all clients."""
    await manager.broadcast({
        "type": "level",
        "data": level
    })


# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
