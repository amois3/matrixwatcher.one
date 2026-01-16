"""Property-based tests for System Sensor.

Feature: matrix-watcher, Property 3: System sensor record completeness
Validates: Requirements 2.2
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.sensors.system_sensor import SystemSensor
from src.sensors.base import SensorConfig


# ============================================================================
# Property 3: System sensor record completeness
# Feature: matrix-watcher, Property 3: System sensor record completeness
# Validates: Requirements 2.2
# ============================================================================

class TestSystemSensorRecordCompleteness:
    """Property 3: All required fields present in system sensor records."""
    
    def test_collect_returns_all_required_fields(self):
        """
        Feature: matrix-watcher, Property 3: System sensor record completeness
        System sensor should return all required fields.
        """
        sensor = SystemSensor()
        data = sensor.collect_data()
        
        required_fields = [
            "local_time_unix",
            "loop_interval_ms",
            "loop_drift_ms",
            "cpu_usage_percent",
            "ram_usage_percent",
            "process_pid",
            "process_uptime_seconds"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_field_types_are_correct(self):
        """
        Feature: matrix-watcher, Property 3: System sensor record completeness
        All fields should have correct types.
        """
        sensor = SystemSensor()
        data = sensor.collect_data()
        
        # Check types
        assert isinstance(data["local_time_unix"], float)
        assert isinstance(data["loop_interval_ms"], float)
        assert isinstance(data["loop_drift_ms"], float)
        assert isinstance(data["cpu_usage_percent"], float)
        assert isinstance(data["ram_usage_percent"], float)
        assert isinstance(data["process_pid"], int)
        assert isinstance(data["process_uptime_seconds"], float)
        
        # cpu_temperature can be None or float
        assert data["cpu_temperature"] is None or isinstance(data["cpu_temperature"], float)
    
    def test_values_are_in_valid_ranges(self):
        """
        Feature: matrix-watcher, Property 3: System sensor record completeness
        Values should be within valid ranges.
        """
        sensor = SystemSensor()
        data = sensor.collect_data()
        
        # Timestamp should be reasonable (after year 2020)
        assert data["local_time_unix"] > 1577836800  # 2020-01-01
        
        # Percentages should be 0-100
        assert 0 <= data["cpu_usage_percent"] <= 100
        assert 0 <= data["ram_usage_percent"] <= 100
        
        # Loop timing should be positive
        assert data["loop_interval_ms"] >= 0
        
        # PID should be positive
        assert data["process_pid"] > 0
        
        # Uptime should be non-negative
        assert data["process_uptime_seconds"] >= 0
    
    @given(
        num_collections=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_multiple_collections_all_have_required_fields(self, num_collections):
        """
        Feature: matrix-watcher, Property 3: System sensor record completeness
        Multiple collections should all return required fields.
        """
        sensor = SystemSensor()
        
        required_fields = [
            "local_time_unix",
            "loop_interval_ms", 
            "loop_drift_ms",
            "cpu_usage_percent",
            "ram_usage_percent",
            "process_pid",
            "process_uptime_seconds"
        ]
        
        for i in range(num_collections):
            data = sensor.collect_data()
            
            for field in required_fields:
                assert field in data, f"Collection {i}: missing field {field}"


class TestSystemSensorFunctionality:
    """Additional System Sensor functionality tests."""
    
    def test_loop_drift_calculation(self):
        """Test that loop drift is calculated correctly."""
        import time
        
        config = SensorConfig(interval_seconds=0.1)
        sensor = SystemSensor(config=config)
        
        # First collection
        sensor.collect_data()
        
        # Wait longer than expected interval
        time.sleep(0.15)
        
        # Second collection
        data = sensor.collect_data()
        
        # Drift should be positive (we waited longer than expected)
        assert data["loop_drift_ms"] > 0
    
    def test_schema_matches_data(self):
        """Test that schema matches actual data fields."""
        sensor = SystemSensor()
        schema = sensor.get_schema()
        data = sensor.collect_data()
        
        # All schema fields should be in data
        for field in schema:
            assert field in data, f"Schema field {field} not in data"
    
    def test_cpu_temperature_graceful_handling(self):
        """Test that missing CPU temperature is handled gracefully."""
        sensor = SystemSensor()
        data = sensor.collect_data()
        
        # Should not raise, temperature can be None
        assert "cpu_temperature" in data
    
    def test_sensor_stats(self):
        """Test sensor statistics tracking."""
        sensor = SystemSensor()
        sensor.start()
        
        # Collect some data
        sensor.collect_data()
        sensor.collect_data()
        
        stats = sensor.get_stats()
        
        assert stats["name"] == "system"
        assert stats["status"] == "running"
        assert stats["uptime_seconds"] >= 0
