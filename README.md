# Matrix Watcher

**Real-time anomaly detection and correlation monitoring across multiple independent data streams.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> *We watch, we don't explain.*

## Overview

Matrix Watcher is an autonomous system that monitors multiple independent data sources in real-time, detecting anomalies and searching for correlations that emerge from chaos. The system observes patterns without attempting to explain them - letting the data speak for itself.

### Live Demo
**[matrixwatcher.space](https://matrixwatcher.space)**

## Data Sources

The system continuously monitors 7 independent sensors:

| Sensor | Description | Update Interval |
|--------|-------------|-----------------|
| **Crypto** | BTC/ETH price movements, volatility | 2 seconds |
| **Blockchain** | Network metrics, block times | 10 seconds |
| **Quantum RNG** | True randomness from quantum fluctuations (ANU) | 5 minutes |
| **Space Weather** | Solar activity, geomagnetic storms | 5 minutes |
| **Seismic** | Global earthquake activity (USGS) | 1 minute |
| **Weather** | Atmospheric pressure, temperature | 5 minutes |
| **News** | Global event streams (RSS feeds) | 5 minutes |

## How It Works

### Anomaly Detection
Each sensor independently detects anomalies using percentage-change thresholds. When a value deviates significantly from recent history, it's flagged as an anomaly.

### Cluster Detection
When anomalies from multiple independent sources occur within a 30-second window, they form a "cluster". Clusters are rated by level:

- **Level 1-2**: Single source anomalies (not displayed)
- **Level 3**: 3 independent sources correlating
- **Level 4**: 4 independent sources correlating
- **Level 5**: 5+ sources - critical anomaly state

### Pattern Learning
The system tracks historical patterns: when condition X occurs, what events follow? Over time, it builds a statistical model of correlations.

### Predictions
Based on learned patterns, the system generates predictions. All statistics shown are **honest and verifiable** - the system never inflates numbers.

## Installation

```bash
# Clone the repository
git clone https://github.com/amois3/matrix_watcher.git
cd matrix_watcher

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure
cp config.example.json config.json
# Edit config.json with your API keys
```

## Configuration

Edit `config.json` to configure:

- **Sensors**: Enable/disable individual sensors, set intervals
- **API Keys**: Add your keys for weather, Telegram alerts, etc.
- **Analysis**: Tune detection thresholds
- **Alerting**: Configure Telegram notifications

### API Keys

| Service | Required | Get it from |
|---------|----------|-------------|
| OpenWeatherMap | Optional | [openweathermap.org](https://openweathermap.org/api) |
| Telegram Bot | Optional | [@BotFather](https://t.me/botfather) |

Most sensors work without API keys (crypto, blockchain, earthquake, space weather, news).

## Usage

### Quick Start

```bash
# Start all services in background
./start_all.sh

# Check status
./status.sh

# Stop all services
./stop_all.sh
```

### Manual Start

```bash
# Start the main sensor system
python3 main.py

# In another terminal, start the web interface
python3 run_pwa.py
```

### View Logs

```bash
tail -f logs/main.log      # Sensor activity
tail -f logs/watchdog.log  # PWA health
```

## Web Interface

The PWA is accessible at `http://localhost:5555` after starting.

Features:
- Real-time anomaly cluster display (Level 3+)
- Active predictions with honest statistics
- Mobile-friendly responsive design
- Works offline (PWA)

## Architecture

```
matrix_watcher/
├── main.py                 # Main entry point
├── run_pwa.py             # Web server launcher
├── pwa_watchdog.py        # Auto-restart on failure
├── src/
│   ├── sensors/           # Data source implementations
│   ├── analyzers/         # Anomaly & pattern detection
│   └── storage/           # Data persistence
├── web/
│   ├── api.py            # FastAPI backend
│   └── static/           # PWA frontend
└── logs/                  # Data storage
```

## Philosophy

Matrix Watcher is built on principles of **honesty and transparency**:

1. **No fake statistics** - All numbers are real and verifiable
2. **No explanations** - We observe correlations, not causation
3. **Open data** - All patterns and predictions come from actual observations
4. **Reproducible** - Same data in = same results out

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [ANU Quantum Random Numbers](https://qrng.anu.edu.au/) - True quantum randomness
- [USGS Earthquake API](https://earthquake.usgs.gov/) - Seismic data
- [NOAA Space Weather](https://www.swpc.noaa.gov/) - Solar activity data
- [Binance API](https://binance.com/) - Cryptocurrency data

---

**Disclaimer**: This project is for educational and research purposes. Predictions are statistical observations, not financial advice. Past correlations do not guarantee future results.
