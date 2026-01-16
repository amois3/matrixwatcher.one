"""Property-based tests for Health Monitor.

Tests:
- Property 49: Sensor status tracking - status tracked for all sensors
- Property 50: Consecutive failure handling - 3 failures triggers disable and alert

Validates: Requirements 19.1, 19.4
"""

import time
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from src.monitoring.health_monitor import HealthMonitor, SensorHealth
from src.core.types import SensorStatus


class TestHealthMonitorProperties:
    """Property-based tests for HealthMonitor."""
    
    @given(
        sensor_names=st.lists(
            st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_49_sensor_status_tracking(self, sensor_names):
        """Property 49: Sensor status tracking.
        
        Status is tracked for all registered sensors.
        """
        monitor = HealthMonitor()
        
        for name in sensor_names:
            monitor.register_sensor(name)
        
        # All sensors should be tracked
        for name in sensor_names:
            status = monitor.get_sensor_status(name)
            assert status is not None
            assert status.name == name
    
    @given(
        failure_threshold=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_property_50_consecutive_failure_handling(self, failure_threshold):
        """Property 50: Consecutive failure handling.
        
        Sensors are disabled after threshold consecutive failures.
        """
        disabled_sensors = []
        
        def on_disabled(name):
            disabled_sensors.append(name)
        
        monitor = HealthMonitor(
            failure_threshold=failure_threshold,
            on_sensor_disabled=on_disabled
        )
        
        monitor.register_sensor("test")
        
        # Record failures up to threshold
        for i in range(failure_threshold):
            monitor.record_failure("test", f"Error {i}")
        
        # Sensor should be disabled
        status = monitor.get_sensor_status("test")
        assert status.disabled == True
        assert "test" in disabled_sensors
    
    @given(
        n_successes=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_success_resets_failures(self, n_successes):
        """Success resets consecutive failure count."""
        monitor = HealthMonitor(failure_threshold=3)
        monitor.register_sensor("test")
        
        # Record some failures
        monitor.record_failure("test")
        monitor.record_failure("test")
        
        # Record success
        monitor.record_success("test")
        
        status = monitor.get_sensor_status("test")
        assert status.consecutive_failures == 0
        assert status.status == SensorStatus.RUNNING


class TestHealthMonitorIntegration:
    """Integration tests for HealthMonitor."""
    
    @pytest.fixture
    def monitor(self):
        return HealthMonitor(port=8080, failure_threshold=3)
    
    def test_register_sensor(self, monitor):
        """Registers sensor correctly."""
        monitor.register_sensor("system")
        
        status = monitor.get_sensor_status("system")
        assert status is not None
        assert status.name == "system"
        assert status.status == SensorStatus.STOPPED
    
    def test_record_success(self, monitor):
        """Records success correctly."""
        monitor.register_sensor("system")
        monitor.record_success("system")
        
        status = monitor.get_sensor_status("system")
        assert status.status == SensorStatus.RUNNING
        assert status.total_successes == 1
        assert status.last_success is not None
    
    def test_record_failure(self, monitor):
        """Records failure correctly."""
        monitor.register_sensor("system")
        monitor.record_failure("system", "Test error")
        
        status = monitor.get_sensor_status("system")
        assert status.status == SensorStatus.ERROR
        assert status.total_failures == 1
        assert status.error_message == "Test error"
    
    def test_record_rate_limit(self, monitor):
        """Records rate limit correctly."""
        monitor.register_sensor("crypto")
        monitor.record_rate_limit("crypto")
        
        status = monitor.get_sensor_status("crypto")
        assert status.status == SensorStatus.RATE_LIMITED
    
    def test_auto_register_on_record(self, monitor):
        """Auto-registers sensor on first record."""
        monitor.record_success("new_sensor")
        
        status = monitor.get_sensor_status("new_sensor")
        assert status is not None
    
    def test_enable_sensor(self, monitor):
        """Re-enables disabled sensor."""
        monitor.register_sensor("test")
        
        # Disable by failures
        for _ in range(3):
            monitor.record_failure("test")
        
        assert monitor.get_sensor_status("test").disabled == True
        
        # Re-enable
        monitor.enable_sensor("test")
        
        status = monitor.get_sensor_status("test")
        assert status.disabled == False
        assert status.consecutive_failures == 0
    
    def test_api_quota_tracking(self, monitor):
        """Tracks API quota usage."""
        monitor.register_api_quota("binance", limit=1200)
        monitor.record_api_usage("binance", 10)
        
        status = monitor.get_all_status()
        assert "binance" in status["api_quotas"]
        assert status["api_quotas"]["binance"]["used"] == 10
        assert status["api_quotas"]["binance"]["remaining"] == 1190
    
    def test_get_all_status(self, monitor):
        """Returns complete status."""
        monitor.register_sensor("system")
        monitor.record_success("system")
        
        status = monitor.get_all_status()
        
        assert "status" in status
        assert "uptime_seconds" in status
        assert "sensors" in status
        assert "sensors_healthy" in status
        assert "sensors_total" in status
        assert "timestamp" in status
    
    def test_nonexistent_sensor(self, monitor):
        """Returns None for nonexistent sensor."""
        status = monitor.get_sensor_status("nonexistent")
        assert status is None
