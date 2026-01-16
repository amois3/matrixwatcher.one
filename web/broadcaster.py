"""Broadcaster for sending updates to PWA clients."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# PWA API endpoint
PWA_API_URL = "http://localhost:8888"


class PWABroadcaster:
    """Broadcasts events to PWA clients via the web API."""
    
    def __init__(self, api_url: str = PWA_API_URL):
        self.api_url = api_url
        self._session: aiohttp.ClientSession | None = None
        self._enabled = True
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def broadcast_prediction(self, prediction: dict) -> bool:
        """Broadcast a new prediction to PWA clients.
        
        Args:
            prediction: Prediction data with keys:
                - condition: str (e.g., "L2_earthquake_quantum_rng")
                - event: str (e.g., "btc_dump_4h")
                - description: str
                - probability: float (0-1)
                - avg_time_hours: float
                - observations: int
                - severity: str
        """
        if not self._enabled:
            return False
        
        try:
            # Format for PWA
            formatted = {
                "id": f"{prediction.get('condition', 'unknown')}_{prediction.get('event', 'unknown')}_{time.time()}",
                "condition": prediction.get("condition", "unknown"),
                "event": prediction.get("event", "unknown"),
                "description": prediction.get("description", "Unknown event"),
                "probability": round(prediction.get("probability", 0) * 100),
                "avg_time_hours": round(prediction.get("avg_time_hours", 0), 1),
                "observations": prediction.get("observations", 0),
                "occurrences": prediction.get("occurrences", 0),
                "icon": self._get_icon(prediction.get("event", "")),
                "color": self._get_color(prediction.get("event", "")),
                "timestamp": time.time()
            }
            
            # Write to shared file for API to pick up
            self._write_event("prediction", formatted)
            logger.debug(f"PWA: Broadcast prediction {formatted['event']}")
            return True
            
        except Exception as e:
            logger.debug(f"PWA broadcast failed: {e}")
            return False
    
    async def broadcast_level(self, level_data: dict) -> bool:
        """Broadcast a new level event to PWA clients.
        
        Args:
            level_data: Level data with keys:
                - level: int (1-5)
                - sources: list[str]
                - index: float
                - status: str
                - timestamp: float
        """
        if not self._enabled:
            return False
        
        try:
            from datetime import datetime
            
            ts = level_data.get("timestamp", time.time())
            
            formatted = {
                "id": f"level_{ts}",
                "level": level_data.get("level", 1),
                "sources": level_data.get("sources", []),
                "sources_str": " + ".join(level_data.get("sources", [])),
                "index": round(level_data.get("index", 0), 1),
                "status": level_data.get("status", "normal"),
                "timestamp": ts,
                "time_str": datetime.fromtimestamp(ts).strftime("%H:%M"),
                "color": self._get_level_color(level_data.get("level", 1))
            }
            
            self._write_event("level", formatted)
            logger.debug(f"PWA: Broadcast level {formatted['level']}")
            return True
            
        except Exception as e:
            logger.debug(f"PWA broadcast failed: {e}")
            return False
    
    def _get_icon(self, event_type: str) -> str:
        """Get icon for event type."""
        if "pump" in event_type:
            return "📈"
        elif "dump" in event_type:
            return "📉"
        elif "volatility" in event_type:
            return "⚡"
        elif "blockchain" in event_type:
            return "⛓️"
        return "🔮"
    
    def _get_color(self, event_type: str) -> str:
        """Get color for event type."""
        if "pump" in event_type:
            return "#00ff88"
        elif "dump" in event_type:
            return "#ff4444"
        elif "volatility" in event_type:
            return "#ffaa00"
        return "#8888ff"
    
    def _get_level_color(self, level: int) -> str:
        """Get color for level."""
        colors = {
            1: "#666666",
            2: "#ffaa00",
            3: "#ff6600",
            4: "#ff3333",
            5: "#ff0000"
        }
        return colors.get(level, "#ffffff")
    
    def _write_event(self, event_type: str, data: dict):
        """Write event to shared file for API."""
        events_dir = Path("web/events")
        events_dir.mkdir(exist_ok=True)
        
        event_file = events_dir / f"{event_type}s.jsonl"
        
        with open(event_file, "a") as f:
            f.write(json.dumps(data) + "\n")
        
        # Keep only last 100 events
        try:
            with open(event_file, "r") as f:
                lines = f.readlines()
            
            if len(lines) > 100:
                with open(event_file, "w") as f:
                    f.writelines(lines[-100:])
        except Exception:
            pass


# Global instance
_broadcaster: PWABroadcaster | None = None


def get_broadcaster() -> PWABroadcaster:
    """Get or create broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = PWABroadcaster()
    return _broadcaster
