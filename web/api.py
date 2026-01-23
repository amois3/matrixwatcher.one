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
    """Load recent anomalies from logs (only level >= 3, deduplicated by minute)."""
    anomalies = []
    logs_path = Path("logs/anomalies")
    
    if not logs_path.exists():
        return anomalies
    
    cutoff = time.time() - (hours * 3600)
    
    # Read more files for longer periods
    days_to_read = max(3, (hours // 24) + 2)
    
    seen_keys = set()  # For deduplication
    
    for log_file in sorted(logs_path.glob("*.jsonl"), reverse=True)[:days_to_read]:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        level = data.get("cluster", {}).get("level", 0)
                        ts = data.get("timestamp", 0)
                        
                        if level >= 3 and ts > cutoff:
                            # Create dedup key: minute + level + sorted sources
                            minute = int(ts // 60)
                            sources = sorted(set(
                                a.get("sensor_source", "") 
                                for a in data.get("cluster", {}).get("anomalies", [])
                            ))
                            dedup_key = f"{minute}_{level}_{'-'.join(sources)}"
                            
                            if dedup_key not in seen_keys:
                                seen_keys.add(dedup_key)
                                anomalies.append(data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading {log_file}: {e}")
    
    anomalies.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return anomalies[:100]


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
    """Get active predictions from file (real-time sync with main.py).
    
    This ensures PWA shows EXACTLY the same data as Telegram.
    File is updated by main.py whenever new predictions are generated.
    """
    predictions_file = Path("logs/predictions/current.json")
    
    if not predictions_file.exists():
        return []
    
    try:
        with open(predictions_file, 'r') as f:
            data = json.load(f)
        
        predictions = data.get("predictions", [])
        last_update = data.get("last_update", 0)
        
        # Filter out old predictions (older than 24 hours)
        cutoff = time.time() - (24 * 3600)
        active_predictions = [
            p for p in predictions 
            if p.get("timestamp", 0) > cutoff
        ]
        
        logger.debug(f"Loaded {len(active_predictions)} active predictions from file (last update: {last_update})")
        return active_predictions
        
    except Exception as e:
        logger.error(f"Error loading predictions from file: {e}")
        return []


def format_level_event(anomaly: dict) -> dict | None:
    """Format anomaly for level display - detailed like Telegram but in English."""
    cluster = anomaly.get("cluster", {})
    index_data = anomaly.get("index", {})
    
    level = cluster.get("level", 0)
    if level < 3:  # Only show Level 3+ (significant correlations)
        return None
    
    timestamp = anomaly.get("timestamp", time.time())
    
    # Get sources with icons
    source_icons = {
        "crypto": "💰",
        "quantum_rng": "🎲", 
        "space_weather": "☀️",
        "weather": "🌤️",
        "earthquake": "🌍",
        "blockchain": "⛓️",
        "news": "📰"
    }
    
    sources = []
    for a in cluster.get("anomalies", []):
        src = a.get("sensor_source", "unknown")
        if src not in sources:
            sources.append(src)
    
    sources_formatted = [f"{source_icons.get(s, '📊')} {s.replace('_', ' ').title()}" for s in sources]
    
    # Level descriptions
    level_names = {
        3: "Multiple Correlation",
        4: "Strong Correlation", 
        5: "Critical Anomaly"
    }
    
    level_icons = {3: "🔴", 4: "🔴🔴", 5: "🚨"}
    
    # Calculate deviation
    index_val = index_data.get("value", 0)
    deviation = round(index_val / 5, 1) if index_val > 0 else 1.0
    
    # Format time in UTC
    dt = datetime.utcfromtimestamp(timestamp)
    today = datetime.utcnow().date()
    if dt.date() == today:
        time_str = dt.strftime("%H:%M UTC")
        date_str = "Today"
    else:
        time_str = dt.strftime("%H:%M UTC")
        date_str = dt.strftime("%d %b")
    
    # System comment based on level
    comments = {
        3: "Stable cluster of deviations detected across multiple independent domains. Observed behavior exceeds normal background.",
        4: "Strong correlation pattern emerging. Multiple sensors showing synchronized anomalous readings.",
        5: "Critical anomaly state. Unprecedented correlation across monitoring systems. Maximum observation priority."
    }
    
    return {
        "id": f"level_{timestamp}",
        "level": level,
        "level_name": level_names.get(level, "Anomaly"),
        "level_icon": level_icons.get(level, "⚠️"),
        "sources": sources,
        "sources_formatted": sources_formatted,
        "sources_str": " + ".join(sources),
        "index": round(index_val, 1),
        "deviation": deviation,
        "status": index_data.get("status", "normal"),
        "timestamp": timestamp,
        "time_str": time_str,
        "date_str": date_str,
        "comment": comments.get(level, "Anomaly detected."),
        "source_count": len(sources)
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


@app.get("/api/all")
async def get_all_data(hours: int = 72):
    """Get all data in one request."""
    # Limit to 7 days max
    hours = min(hours, 168)
    
    anomalies = load_recent_anomalies(hours)
    level_list = [format_level_event(a) for a in anomalies if format_level_event(a)]
    
    return {
        "predictions": get_active_predictions(),
        "levels": level_list,
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
