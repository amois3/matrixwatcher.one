#!/usr/bin/env python3
"""Matrix Watcher Web Server - Simple Flask backend."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, Response
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')


def load_recent_anomalies(hours: int = 24) -> list:
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
    except Exception:
        return {}


def get_active_predictions() -> list:
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
        
        # IMPORTANT: PWA shows ALL predictions (including 100%)
        # Unlike Telegram which filters 40-95% only
        # This is intentional - PWA is for monitoring, not notifications
        
        logger.debug(f"Loaded {len(active_predictions)} active predictions from file (last update: {last_update})")
        return active_predictions
        
    except Exception as e:
        logger.error(f"Error loading predictions from file: {e}")
        return []


def format_level_event(anomaly: dict):
    """Format anomaly for level display - detailed like Telegram but in English."""
    cluster = anomaly.get("cluster", {})
    index_data = anomaly.get("index", {})
    
    level = cluster.get("level", 0)
    if level < 3:
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


@app.route('/')
def index():
    response = send_from_directory('static', 'index.html')
    # Disable cache for index.html to ensure users get latest version
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})


@app.route('/api/predictions')
def predictions():
    return jsonify({"predictions": get_active_predictions()})


@app.route('/api/levels')
def levels():
    anomalies = load_recent_anomalies(24)
    level_list = []
    
    for a in anomalies:
        formatted = format_level_event(a)
        if formatted:
            level_list.append(formatted)
    
    return jsonify({"levels": level_list[:30]})


@app.route('/api/all')
def all_data():
    """Get all data in one request."""
    from flask import request
    hours = request.args.get('hours', 72, type=int)
    
    # Limit to 7 days max
    hours = min(hours, 168)
    
    anomalies = load_recent_anomalies(hours)
    level_list = [format_level_event(a) for a in anomalies if format_level_event(a)]
    
    return jsonify({
        "predictions": get_active_predictions(),
        "levels": level_list,  # Return all loaded
        "timestamp": time.time()
    })


@app.route('/api/stream')
def stream():
    """Server-Sent Events stream for real-time updates."""
    def generate():
        last_check = time.time()
        
        while True:
            time.sleep(5)  # Check every 5 seconds
            
            # Get latest data
            anomalies = load_recent_anomalies(1)  # Last hour
            new_levels = []
            
            for a in anomalies:
                if a.get("timestamp", 0) > last_check:
                    formatted = format_level_event(a)
                    if formatted:
                        new_levels.append(formatted)
            
            if new_levels:
                data = json.dumps({"type": "levels", "data": new_levels})
                yield f"data: {data}\n\n"
            
            # Send heartbeat
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
            last_check = time.time()
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5555))
    print(f"🌐 Starting Matrix Watcher PWA on port {port}...")
    print(f"📱 Open http://localhost:{port} in your browser")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
