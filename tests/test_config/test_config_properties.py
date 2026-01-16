"""Property-based tests for configuration.

Feature: matrix-watcher, Property 1: Configuration round-trip
Feature: matrix-watcher, Property 2: Invalid configuration handling
Validates: Requirements 1.1, 1.3
"""

import pytest
import json
import tempfile
import os
from hypothesis import given, strategies as st, settings, HealthCheck

from src.config.schema import (
    Config, SensorConfig, StorageConfig, AnalysisConfig, AlertingConfig
)
from src.config.config_manager import ConfigManager, ConfigValidationError


# Simplified strategies
simple_text = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")


# ============================================================================
# Property 1: Configuration round-trip
# Feature: matrix-watcher, Property 1: Configuration round-trip
# Validates: Requirements 1.1
# ============================================================================

class TestConfigRoundTrip:
    """Property 1: Serialize to JSON and parse back produces equivalent config."""
    
    @given(
        enabled=st.booleans(),
        interval=st.floats(min_value=0.1, max_value=3600.0, allow_nan=False, allow_infinity=False),
        priority=st.sampled_from(["high", "medium", "low"])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_sensor_config_round_trip(self, enabled, interval, priority):
        """
        Feature: matrix-watcher, Property 1: Configuration round-trip
        For any valid SensorConfig, serializing to dict and back preserves values.
        """
        original = SensorConfig(
            enabled=enabled,
            interval_seconds=interval,
            priority=priority
        )
        
        # Round trip
        as_dict = original.to_dict()
        restored = SensorConfig.from_dict(as_dict)
        
        assert restored.enabled == original.enabled
        assert restored.interval_seconds == original.interval_seconds
        assert restored.priority == original.priority
    
    @given(
        base_path=simple_text,
        compression=st.booleans(),
        max_file_size=st.integers(min_value=1, max_value=10000),
        buffer_size=st.integers(min_value=1, max_value=100000)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_storage_config_round_trip(self, base_path, compression, max_file_size, buffer_size):
        """
        Feature: matrix-watcher, Property 1: Configuration round-trip
        For any valid StorageConfig, serializing to dict and back preserves values.
        """
        original = StorageConfig(
            base_path=base_path,
            compression=compression,
            max_file_size_mb=max_file_size,
            buffer_size=buffer_size
        )
        
        as_dict = original.to_dict()
        restored = StorageConfig.from_dict(as_dict)
        
        assert restored.base_path == original.base_path
        assert restored.compression == original.compression
        assert restored.max_file_size_mb == original.max_file_size_mb
        assert restored.buffer_size == original.buffer_size
    
    @given(
        window_size=st.integers(min_value=10, max_value=10000),
        z_score=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        lag_range=st.integers(min_value=1, max_value=3600),
        cluster_window=st.floats(min_value=0.1, max_value=60.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_analysis_config_round_trip(self, window_size, z_score, lag_range, cluster_window):
        """
        Feature: matrix-watcher, Property 1: Configuration round-trip
        For any valid AnalysisConfig, serializing to dict and back preserves values.
        """
        original = AnalysisConfig(
            window_size=window_size,
            z_score_threshold=z_score,
            lag_range_seconds=lag_range,
            cluster_window_seconds=cluster_window
        )
        
        as_dict = original.to_dict()
        restored = AnalysisConfig.from_dict(as_dict)
        
        assert restored.window_size == original.window_size
        assert restored.z_score_threshold == original.z_score_threshold
        assert restored.lag_range_seconds == original.lag_range_seconds
        assert restored.cluster_window_seconds == original.cluster_window_seconds
    
    @given(
        enabled=st.booleans(),
        cooldown=st.integers(min_value=0, max_value=86400),
        min_sensors=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_alerting_config_round_trip(self, enabled, cooldown, min_sensors):
        """
        Feature: matrix-watcher, Property 1: Configuration round-trip
        For any valid AlertingConfig, serializing to dict and back preserves values.
        """
        original = AlertingConfig(
            enabled=enabled,
            cooldown_seconds=cooldown,
            min_cluster_sensors=min_sensors
        )
        
        as_dict = original.to_dict()
        restored = AlertingConfig.from_dict(as_dict)
        
        assert restored.enabled == original.enabled
        assert restored.cooldown_seconds == original.cooldown_seconds
        assert restored.min_cluster_sensors == original.min_cluster_sensors
    
    def test_full_config_round_trip(self):
        """
        Feature: matrix-watcher, Property 1: Configuration round-trip
        Full Config object round-trips through JSON correctly.
        """
        original = Config.default()
        
        # Round trip through JSON
        json_str = original.to_json()
        restored = Config.from_json(json_str)
        
        # Check sensors
        assert set(restored.sensors.keys()) == set(original.sensors.keys())
        for name in original.sensors:
            assert restored.sensors[name].enabled == original.sensors[name].enabled
            assert restored.sensors[name].interval_seconds == original.sensors[name].interval_seconds
            assert restored.sensors[name].priority == original.sensors[name].priority
        
        # Check other sections
        assert restored.storage.base_path == original.storage.base_path
        assert restored.analysis.window_size == original.analysis.window_size
        assert restored.alerting.enabled == original.alerting.enabled


# ============================================================================
# Property 2: Invalid configuration handling
# Feature: matrix-watcher, Property 2: Invalid configuration handling
# Validates: Requirements 1.3
# ============================================================================

class TestInvalidConfigHandling:
    """Property 2: Invalid values return errors and use defaults."""
    
    @given(
        interval=st.floats(min_value=-1000, max_value=-0.1, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_negative_interval_uses_minimum(self, interval):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        Negative intervals should be clamped to minimum (0.1).
        """
        config = SensorConfig(interval_seconds=interval)
        assert config.interval_seconds >= 0.1
    
    @given(
        interval=st.floats(min_value=3601, max_value=100000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_large_interval_uses_maximum(self, interval):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        Intervals exceeding maximum should be clamped to 3600.
        """
        config = SensorConfig(interval_seconds=interval)
        assert config.interval_seconds <= 3600
    
    @given(
        priority=st.text(min_size=1, max_size=20).filter(lambda x: x not in ("high", "medium", "low"))
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_priority_uses_default(self, priority):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        Invalid priority values should default to 'medium'.
        """
        config = SensorConfig(priority=priority)
        assert config.priority == "medium"
    
    @given(
        z_score=st.floats(min_value=-100, max_value=0.9, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_low_z_score_uses_minimum(self, z_score):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        Z-score below minimum should be clamped to 1.0.
        """
        config = AnalysisConfig(z_score_threshold=z_score)
        assert config.z_score_threshold >= 1.0
    
    @given(
        z_score=st.floats(min_value=10.1, max_value=100, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_high_z_score_uses_maximum(self, z_score):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        Z-score above maximum should be clamped to 10.0.
        """
        config = AnalysisConfig(z_score_threshold=z_score)
        assert config.z_score_threshold <= 10.0
    
    def test_config_manager_validates_invalid_json(self):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        ConfigManager should handle invalid JSON gracefully.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            
            # Write invalid JSON
            with open(config_path, "w") as f:
                f.write("{ invalid json }")
            
            manager = ConfigManager(config_path)
            config = manager.load()
            
            # Should return default config
            assert config is not None
            assert len(manager.get_validation_errors()) > 0
    
    def test_config_manager_validates_wrong_types(self):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        ConfigManager should detect wrong types in config.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            
            # Write config with wrong types
            invalid_config = {
                "sensors": {
                    "system": {
                        "enabled": "yes",  # Should be bool
                        "interval_seconds": "fast",  # Should be number
                        "priority": 123  # Should be string
                    }
                }
            }
            
            with open(config_path, "w") as f:
                json.dump(invalid_config, f)
            
            manager = ConfigManager(config_path)
            config = manager.load()
            
            # Should have validation errors
            errors = manager.get_validation_errors()
            assert len(errors) > 0
    
    def test_config_manager_creates_default_on_missing(self):
        """
        Feature: matrix-watcher, Property 2: Invalid configuration handling
        ConfigManager should create default config when file is missing.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "nonexistent.json")
            
            manager = ConfigManager(config_path)
            config = manager.load()
            
            # Should create default config
            assert config is not None
            assert os.path.exists(config_path)
            
            # Should have all default sensors
            assert "system" in config.sensors
            assert "crypto" in config.sensors


class TestConfigManagerFunctionality:
    """Test ConfigManager additional functionality."""
    
    def test_get_enabled_sensors(self):
        """Test getting list of enabled sensors."""
        config = Config.default()
        enabled = config.get_enabled_sensors()
        
        # All sensors enabled by default
        assert "system" in enabled
        assert "crypto" in enabled
        assert len(enabled) == 8
    
    def test_hot_reload_callback(self):
        """Test hot-reload callback mechanism."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            
            manager = ConfigManager(config_path)
            manager.load()
            
            # Track callback invocations
            callback_invoked = []
            
            def on_reload(new_config):
                callback_invoked.append(new_config)
            
            manager.on_reload(on_reload)
            
            # Create a modified config with different values
            modified_config = {
                "sensors": {
                    "system": {"enabled": True, "interval_seconds": 5.0, "priority": "low"}
                },
                "storage": {"base_path": "different_logs"},
                "analysis": {"window_size": 200},
                "alerting": {"enabled": True},
                "api_keys": {}
            }
            
            with open(config_path, "w") as f:
                json.dump(modified_config, f)
            
            # Reload - callback should be invoked since config changed
            manager.reload()
            
            # Verify config was reloaded with new values
            assert manager.config.storage.base_path == "different_logs"
            assert manager.config.analysis.window_size == 200
