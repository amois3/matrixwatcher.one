# Requirements Document

## Introduction

Matrix Watcher v1.0 — автономный программный комплекс для поиска скрытых закономерностей и аномалий в цифровой реальности. Система собирает многослойные данные из независимых источников (время, сеть, генераторы случайности, криптовалютные биржи, блокчейн, погода, новости), хранит их в структурированных логах и анализирует в реальном времени и оффлайн для обнаружения скрытых корреляций, lag-корреляций, редких совпадений событий и аномальных паттернов.

## Glossary

- **Matrix Watcher**: Основная система мониторинга и анализа данных
- **Sensor**: Модуль сбора данных из конкретного источника
- **Anomaly**: Значение, отклоняющееся от нормы более чем на 4 стандартных отклонения
- **Lag-correlation**: Корреляция между параметрами со сдвигом во времени
- **Z-score**: Статистическая мера отклонения значения от среднего в единицах стандартного отклонения
- **JSONL**: JSON Lines — формат хранения, где каждая строка файла является отдельным JSON-объектом
- **Event Bus**: Центральный механизм передачи данных между компонентами системы
- **Scheduler**: Планировщик задач с поддержкой разных интервалов опроса
- **Health Monitor**: Компонент мониторинга состояния самой системы
- **Parquet**: Колоночный формат хранения данных для эффективного анализа больших объёмов

## Requirements

### Requirement 1: Configuration Management

**User Story:** As a system administrator, I want to configure all system parameters through a single configuration file, so that I can easily customize sensor behavior, API keys, and analysis thresholds.

#### Acceptance Criteria

1. WHEN the Matrix Watcher starts THEN the system SHALL load configuration from `config.json` file in the root directory
2. WHEN configuration file is missing THEN the system SHALL create a default configuration file with all parameters set to safe defaults
3. WHEN configuration contains invalid values THEN the system SHALL log specific validation errors and use default values for invalid parameters
4. WHEN configuration is updated THEN the system SHALL support hot-reload without full system restart
5. THE configuration file SHALL contain sections for: enabled sensors, polling intervals, API keys, crypto pairs, network targets, anomaly thresholds, and storage settings

### Requirement 2: System Sensor

**User Story:** As a data analyst, I want to collect internal system metrics, so that I can correlate system behavior with external data anomalies.

#### Acceptance Criteria

1. WHEN the System Sensor is enabled THEN the system SHALL collect metrics every 1 second
2. THE System Sensor SHALL record: local_time_unix, loop_interval_ms, loop_drift_ms, cpu_usage_percent, ram_usage_percent, cpu_temperature (when available), process_pid, and process_uptime_seconds
3. WHEN CPU temperature is unavailable THEN the system SHALL record null value and continue operation
4. WHEN a metric collection fails THEN the system SHALL log the error and continue collecting other metrics

### Requirement 3: Time Drift Sensor

**User Story:** As a researcher, I want to monitor time synchronization across different sources, so that I can detect temporal anomalies and drift patterns.

#### Acceptance Criteria

1. WHEN the Time Drift Sensor is enabled THEN the system SHALL collect time data every 2 seconds
2. THE Time Drift Sensor SHALL query: local OS time, NTP server time, and external API time (Binance serverTime)
3. THE Time Drift Sensor SHALL calculate and record: local_time, ntp_time, api_time, diff_local_ntp_ms, diff_local_api_ms
4. WHEN NTP server is unreachable THEN the system SHALL retry with backup NTP server and log the failure
5. WHEN external API is unreachable THEN the system SHALL record null for api_time and continue operation

### Requirement 4: Network Sensor

**User Story:** As a network analyst, I want to monitor network latency to key endpoints, so that I can detect network anomalies and correlate them with other data sources.

#### Acceptance Criteria

1. WHEN the Network Sensor is enabled THEN the system SHALL probe network targets every 5 seconds
2. THE Network Sensor SHALL probe: google.com, binance.com, cloudflare.com, and random.org
3. THE Network Sensor SHALL record for each target: target_host, latency_ms, status_code, response_size_bytes
4. WHEN a target is unreachable THEN the system SHALL record latency as -1 and status_code as 0
5. WHEN probe timeout exceeds 10 seconds THEN the system SHALL abort the probe and record timeout status

### Requirement 5: Random Sensor

**User Story:** As a randomness researcher, I want to collect and analyze random number generation from multiple sources, so that I can detect statistical anomalies in randomness.

#### Acceptance Criteria

1. WHEN the Random Sensor is enabled THEN the system SHALL generate random samples every 5 seconds
2. THE Random Sensor SHALL collect samples from: Python random.random(), os.urandom(), and random.org API (when configured)
3. THE Random Sensor SHALL generate batches of 1024 random values per source per interval
4. THE Random Sensor SHALL calculate and record: raw_values (as bit strings), zeros_count, ones_count, chi_square, p_value
5. WHEN random.org API is unavailable THEN the system SHALL continue with local sources and log the failure
6. WHEN chi_square test indicates non-randomness (p_value < 0.01) THEN the system SHALL flag the sample as anomalous

### Requirement 6: Crypto Market Sensor

**User Story:** As a market analyst, I want to collect real-time cryptocurrency market data, so that I can correlate market movements with other system anomalies.

#### Acceptance Criteria

1. WHEN the Crypto Market Sensor is enabled THEN the system SHALL collect market data every 2 seconds
2. THE Crypto Market Sensor SHALL monitor configurable trading pairs (default: BTC/USDT, ETH/USDT)
3. THE Crypto Market Sensor SHALL record: symbol, price, best_bid, best_ask, spread, volume_24h, trade_id, price_delta_percent
4. WHEN exchange API returns rate limit error THEN the system SHALL implement exponential backoff starting at 1 second
5. WHEN price_delta_percent exceeds configured threshold THEN the system SHALL flag the event as significant

### Requirement 7: Blockchain Sensor

**User Story:** As a blockchain researcher, I want to monitor blockchain network metrics, so that I can detect block timing anomalies and correlate them with other data.

#### Acceptance Criteria

1. WHEN the Blockchain Sensor is enabled THEN the system SHALL collect blockchain data every 10 seconds
2. THE Blockchain Sensor SHALL monitor configurable networks (default: Ethereum, Bitcoin)
3. THE Blockchain Sensor SHALL record: network, block_height, block_hash, block_time, tx_count, gas_used, gas_limit, difficulty, block_interval_sec
4. WHEN blockchain API is unavailable THEN the system SHALL retry with backup API endpoint
5. WHEN block_interval_sec deviates more than 50% from expected THEN the system SHALL flag the block as anomalous

### Requirement 8: Weather Sensor

**User Story:** As an environmental data analyst, I want to collect weather data, so that I can explore correlations between environmental conditions and digital system behavior.

#### Acceptance Criteria

1. WHEN the Weather Sensor is enabled THEN the system SHALL collect weather data every 5 minutes
2. THE Weather Sensor SHALL record: temperature_celsius, humidity_percent, pressure_hpa, clouds_percent, wind_speed_ms, location_coordinates
3. WHEN weather API is unavailable THEN the system SHALL use cached last known values and log the failure
4. THE Weather Sensor SHALL support configurable location (default: system IP geolocation)

### Requirement 9: News Sensor

**User Story:** As an information analyst, I want to monitor news feed metadata, so that I can correlate information flow patterns with other system anomalies.

#### Acceptance Criteria

1. WHEN the News Sensor is enabled THEN the system SHALL collect news data every 15 minutes
2. THE News Sensor SHALL record: source, headline, headline_hash, text_length, word_count, text_entropy
3. THE News Sensor SHALL monitor configurable news sources (RSS feeds, news APIs)
4. WHEN news source is unavailable THEN the system SHALL continue with available sources and log the failure
5. THE News Sensor SHALL calculate text_entropy using Shannon entropy formula

### Requirement 10: Data Storage

**User Story:** As a system operator, I want reliable and organized data storage, so that I can perform long-term analysis on collected data.

#### Acceptance Criteria

1. THE system SHALL store sensor data in JSONL format at `logs/{sensor_name}/{YYYY-MM-DD}.jsonl`
2. THE system SHALL store all anomaly events at `logs/anomalies/{YYYY-MM-DD}.jsonl`
3. THE system SHALL store aggregated events at `logs/all_events/{YYYY-MM-DD}.jsonl`
4. WHEN a log file exceeds 100MB THEN the system SHALL rotate to a new file with incremental suffix
5. THE system SHALL support export to Parquet format for efficient offline analysis
6. WHEN writing to storage fails THEN the system SHALL buffer data in memory and retry with exponential backoff
7. THE system SHALL include timestamp (float), source, and sensor-specific fields in every record
8. THE system SHALL implement pretty-printer for JSONL records to enable human-readable output
9. WHEN parsing stored JSONL data THEN the system SHALL validate record structure against expected schema
10. THE system SHALL retain all raw data indefinitely by default (no automatic deletion)
11. THE system SHALL support optional gzip compression for JSONL files via configuration

### Requirement 23: External Storage Integration (Future)

**User Story:** As a system operator, I want to optionally store data in external storage systems, so that I can scale storage capacity beyond local disk.

#### Acceptance Criteria

1. THE system SHALL define a storage backend interface for pluggable storage implementations
2. THE system SHALL support local filesystem as the default storage backend
3. THE system SHALL support MongoDB as an optional storage backend (future implementation)
4. THE system SHALL support Google Drive as an optional storage backend (future implementation)
5. WHEN external storage is configured THEN the system SHALL sync data according to configurable schedule
6. WHEN external storage is unavailable THEN the system SHALL continue writing to local storage and queue for sync

### Requirement 11: Online Anomaly Detector

**User Story:** As a real-time analyst, I want automatic anomaly detection, so that I can be alerted to unusual patterns as they occur.

#### Acceptance Criteria

1. THE Online Anomaly Detector SHALL maintain sliding windows of last N values for each monitored parameter
2. THE Online Anomaly Detector SHALL calculate mean, standard deviation, and z-score for each new value
3. WHEN absolute z-score exceeds 4.0 THEN the system SHALL classify the value as anomaly and write to anomaly log
4. THE Online Anomaly Detector SHALL support configurable window sizes per parameter (default: 100 values)
5. THE Online Anomaly Detector SHALL support configurable z-score thresholds per parameter
6. WHEN anomaly is detected THEN the system SHALL record: timestamp, parameter_name, value, mean, std, z_score, sensor_source

### Requirement 12: Offline Correlation Analyzer

**User Story:** As a data scientist, I want to analyze correlations between all collected parameters, so that I can discover hidden relationships between independent systems.

#### Acceptance Criteria

1. WHEN correlation analysis is requested THEN the system SHALL build full correlation matrix between all numeric parameters
2. THE Correlation Analyzer SHALL calculate Pearson correlation coefficients for all parameter pairs
3. THE Correlation Analyzer SHALL generate heatmap visualization of correlation matrix
4. THE Correlation Analyzer SHALL highlight correlations with absolute value exceeding 0.7
5. WHEN correlation analysis completes THEN the system SHALL export results to CSV and PNG formats

### Requirement 13: Lag-Correlation Analyzer

**User Story:** As a causality researcher, I want to analyze time-shifted correlations, so that I can discover predictive relationships and delayed effects between parameters.

#### Acceptance Criteria

1. WHEN lag-correlation analysis is requested THEN the system SHALL test time shifts from -60 to +60 seconds
2. THE Lag-Correlation Analyzer SHALL find optimal lag for maximum correlation for each parameter pair
3. THE Lag-Correlation Analyzer SHALL record: parameter_a, parameter_b, optimal_lag_seconds, max_correlation, correlation_at_zero_lag
4. WHEN optimal lag differs significantly from zero THEN the system SHALL flag the pair as having potential causal relationship
5. THE Lag-Correlation Analyzer SHALL generate lag-correlation plots for significant pairs

### Requirement 14: Cluster Analyzer

**User Story:** As a pattern researcher, I want to find clusters of co-occurring anomalies, so that I can identify systemic events affecting multiple data sources simultaneously.

#### Acceptance Criteria

1. WHEN cluster analysis is requested THEN the system SHALL group anomalies occurring within ±3 seconds
2. THE Cluster Analyzer SHALL build graph where anomalies are nodes and temporal proximity creates edges
3. THE Cluster Analyzer SHALL identify connected components as anomaly clusters
4. THE Cluster Analyzer SHALL rank clusters by: number of distinct sensors involved, total anomaly count, time span
5. WHEN cluster involves 3 or more distinct sensors THEN the system SHALL flag it as significant multi-source event

### Requirement 15: Precursor Pattern Analyzer

**User Story:** As a predictive analyst, I want to identify patterns that precede anomalies, so that I can potentially predict future anomalies.

#### Acceptance Criteria

1. WHEN precursor analysis is requested THEN the system SHALL examine data windows at 5, 10, and 30 seconds before each anomaly
2. THE Precursor Analyzer SHALL identify recurring patterns in pre-anomaly windows
3. THE Precursor Analyzer SHALL calculate pattern frequency and confidence scores
4. WHEN a pattern appears before more than 30% of anomalies of same type THEN the system SHALL flag it as potential precursor
5. THE Precursor Analyzer SHALL generate report of identified precursor patterns with statistical significance

### Requirement 16: Advanced Statistical Analyzer

**User Story:** As a statistical researcher, I want to apply advanced analysis methods, so that I can detect non-linear relationships and periodic patterns.

#### Acceptance Criteria

1. THE Advanced Analyzer SHALL calculate mutual information between parameter pairs
2. THE Advanced Analyzer SHALL perform FFT analysis to detect periodic patterns in anomaly occurrence
3. THE Advanced Analyzer SHALL calculate entropy-based correlation metrics
4. WHEN periodic pattern is detected with period less than 24 hours THEN the system SHALL flag it as significant
5. THE Advanced Analyzer SHALL generate frequency spectrum plots for parameters with detected periodicity

### Requirement 17: Event Bus

**User Story:** As a system architect, I want a central event distribution mechanism, so that components can communicate efficiently and the system can be easily extended.

#### Acceptance Criteria

1. THE Event Bus SHALL support publish-subscribe pattern for sensor data distribution
2. THE Event Bus SHALL support multiple subscribers per event type
3. THE Event Bus SHALL buffer events when subscribers are slow (max 1000 events per subscriber)
4. WHEN buffer overflow occurs THEN the system SHALL drop oldest events and log warning
5. THE Event Bus SHALL support event filtering by sensor type and severity level

### Requirement 18: Scheduler

**User Story:** As a system operator, I want intelligent task scheduling, so that sensors with different intervals can operate efficiently without conflicts.

#### Acceptance Criteria

1. THE Scheduler SHALL support configurable intervals per sensor (1 second to 1 hour)
2. THE Scheduler SHALL prevent sensor execution overlap for same sensor type
3. THE Scheduler SHALL support priority levels for sensors (high, medium, low)
4. WHEN system is under high load THEN the Scheduler SHALL delay low-priority sensors
5. THE Scheduler SHALL log execution timing and drift for each sensor run

### Requirement 19: Health Monitor

**User Story:** As a system administrator, I want to monitor the health of Matrix Watcher itself, so that I can ensure reliable data collection and detect internal issues.

#### Acceptance Criteria

1. THE Health Monitor SHALL track status of each sensor (running, stopped, error, rate-limited)
2. THE Health Monitor SHALL track API quota usage for external services
3. THE Health Monitor SHALL detect and report sensor failures within 30 seconds
4. WHEN sensor fails 3 consecutive times THEN the system SHALL disable sensor and alert operator
5. THE Health Monitor SHALL expose health status via local HTTP endpoint (port 8080)
6. THE Health Monitor SHALL record health metrics to dedicated log file

### Requirement 20: CLI Interface

**User Story:** As a user, I want command-line tools for analysis, so that I can run specific analyses and generate reports on demand.

#### Acceptance Criteria

1. THE CLI SHALL support command: `python analyze.py correlations` for correlation matrix
2. THE CLI SHALL support command: `python analyze.py lag` for lag-correlation analysis
3. THE CLI SHALL support command: `python analyze.py anomalies` for anomaly summary
4. THE CLI SHALL support command: `python analyze.py clusters` for cluster analysis
5. THE CLI SHALL support command: `python analyze.py timeline` for timeline visualization
6. THE CLI SHALL support `--start-date` and `--end-date` parameters for all commands
7. THE CLI SHALL support `--output` parameter to specify output file path
8. THE CLI SHALL display progress indicators for long-running analyses

### Requirement 21: Alerting System

**User Story:** As a researcher, I want to receive notifications about significant findings, so that I can respond to interesting patterns without constant monitoring.

#### Acceptance Criteria

1. THE Alerting System SHALL support webhook notifications (Discord, Telegram, Slack)
2. THE Alerting System SHALL send alerts for: multi-source anomaly clusters, significant correlations discovered, sensor failures
3. THE Alerting System SHALL support configurable alert thresholds and cooldown periods
4. WHEN cooldown period is active THEN the system SHALL suppress duplicate alerts
5. THE Alerting System SHALL include relevant data summary in alert messages

### Requirement 22: Data Export and Replay

**User Story:** As a data scientist, I want to export data and replay historical data through analyzers, so that I can refine analysis parameters and validate findings.

#### Acceptance Criteria

1. THE system SHALL support export to Parquet format with configurable date range
2. THE system SHALL support replay mode that feeds historical data through analyzers
3. WHEN replay mode is active THEN the system SHALL use historical timestamps for analysis
4. THE replay system SHALL support configurable playback speed (1x to 100x)
5. THE system SHALL support export to CSV format for external analysis tools
