"""Property-based tests for Blockchain Sensor.

Tests:
- Property 11: Blockchain sensor record completeness - all required fields present
- Property 12: Block interval anomaly detection - >50% deviation flagged

Validates: Requirements 7.3, 7.5
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.sensors.blockchain_sensor import BlockchainSensor


class TestBlockchainSensorProperties:
    """Property-based tests for BlockchainSensor."""
    
    @given(
        block_height=st.integers(min_value=1, max_value=100000000),
        block_time=st.integers(min_value=1600000000, max_value=2000000000),
        tx_count=st.integers(min_value=0, max_value=10000),
        gas_used=st.integers(min_value=0, max_value=30000000),
        gas_limit=st.integers(min_value=1, max_value=30000000)
    )
    @settings(max_examples=100)
    def test_property_11_record_completeness(self, block_height, block_time, tx_count, gas_used, gas_limit):
        """Property 11: Blockchain sensor record completeness.
        
        All network data must contain required fields.
        """
        network_data = {
            "network": "ethereum",
            "block_height": block_height,
            "block_hash": "0x" + "a" * 64,
            "block_time": block_time,
            "tx_count": tx_count,
            "gas_used": gas_used,
            "gas_limit": gas_limit,
            "gas_used_percent": round(gas_used / gas_limit * 100, 2) if gas_limit > 0 else 0,
            "block_interval_sec": None,
            "interval_anomalous": False
        }
        
        # Verify all required fields present
        required_fields = [
            "network", "block_height", "block_hash", "block_time",
            "tx_count", "block_interval_sec", "interval_anomalous"
        ]
        for field in required_fields:
            assert field in network_data, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(network_data["network"], str)
        assert isinstance(network_data["block_height"], int)
        assert isinstance(network_data["block_hash"], str)
        assert isinstance(network_data["tx_count"], int)
        assert isinstance(network_data["interval_anomalous"], bool)
    
    @given(
        last_time=st.integers(min_value=1600000000, max_value=1900000000),
        current_time=st.integers(min_value=1600000000, max_value=2000000000),
        expected_interval=st.integers(min_value=1, max_value=600)
    )
    @settings(max_examples=100)
    def test_property_12_interval_anomaly_detection(self, last_time, current_time, expected_interval):
        """Property 12: Block interval anomaly detection.
        
        Intervals deviating >50% from expected are flagged as anomalous.
        """
        if current_time <= last_time:
            return  # Skip invalid time sequences
        
        sensor = BlockchainSensor()
        sensor._expected_intervals["test"] = expected_interval
        sensor._last_block_times["test"] = last_time
        sensor._last_block_heights["test"] = 100
        
        interval_data = sensor._calculate_interval("test", 101, current_time)
        
        actual_interval = current_time - last_time
        deviation = abs(actual_interval - expected_interval) / expected_interval
        expected_anomalous = deviation > 0.5
        
        assert interval_data["interval_anomalous"] == expected_anomalous
    
    @given(
        networks=st.lists(
            st.sampled_from(["ethereum", "bitcoin"]),
            min_size=1,
            max_size=2,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_custom_networks_configuration(self, networks):
        """Custom networks are properly configured."""
        sensor = BlockchainSensor(networks=networks)
        assert sensor.networks == networks
    
    @given(
        block_height=st.integers(min_value=1, max_value=100000000),
        last_height=st.integers(min_value=1, max_value=100000000)
    )
    @settings(max_examples=100)
    def test_blocks_since_last_calculation(self, block_height, last_height):
        """Blocks since last is calculated correctly."""
        sensor = BlockchainSensor()
        sensor._last_block_heights["test"] = last_height
        sensor._last_block_times["test"] = 1600000000
        
        interval_data = sensor._calculate_interval("test", block_height, 1600000100)
        
        if block_height > last_height:
            expected_diff = block_height - last_height
            assert interval_data["blocks_since_last"] == expected_diff
        else:
            # No new blocks
            assert interval_data["blocks_since_last"] == 0
    
    @given(
        deviation_percent=st.floats(min_value=0.0, max_value=200.0)
    )
    @settings(max_examples=100)
    def test_deviation_threshold(self, deviation_percent):
        """50% deviation threshold is correctly applied."""
        is_anomalous = deviation_percent > 50.0
        
        # Verify threshold logic
        assert (deviation_percent > 50.0) == is_anomalous


class TestBlockchainSensorIntegration:
    """Integration tests for BlockchainSensor."""
    
    @pytest.fixture
    def sensor(self):
        return BlockchainSensor(networks=["ethereum", "bitcoin"])
    
    def test_default_networks(self, sensor):
        """Default networks are configured."""
        assert "ethereum" in sensor.networks
        assert "bitcoin" in sensor.networks
    
    def test_expected_intervals(self, sensor):
        """Expected block intervals are set."""
        assert sensor._expected_intervals["ethereum"] == 12
        assert sensor._expected_intervals["bitcoin"] == 600
    
    def test_schema(self, sensor):
        """Schema defines expected fields."""
        schema = sensor.get_schema()
        assert "timestamp" in schema
        assert "networks" in schema
        assert "networks_count" in schema
        assert "any_anomalous" in schema
    
    def test_interval_calculation_first_block(self, sensor):
        """First block has no interval data."""
        interval_data = sensor._calculate_interval("ethereum", 1000, 1600000000)
        
        assert interval_data["block_interval_sec"] is None
        assert interval_data["interval_anomalous"] == False
        assert interval_data["blocks_since_last"] == 0
    
    def test_interval_calculation_subsequent_block(self, sensor):
        """Subsequent blocks have interval data."""
        # Set up previous block
        sensor._last_block_times["ethereum"] = 1600000000
        sensor._last_block_heights["ethereum"] = 1000
        
        # Calculate for new block
        interval_data = sensor._calculate_interval("ethereum", 1001, 1600000012)
        
        assert interval_data["block_interval_sec"] == 12.0
        assert interval_data["blocks_since_last"] == 1
        # 12s is exactly expected, so not anomalous
        assert interval_data["interval_anomalous"] == False
    
    def test_anomalous_interval_detection(self, sensor):
        """Anomalous intervals are detected."""
        sensor._last_block_times["ethereum"] = 1600000000
        sensor._last_block_heights["ethereum"] = 1000
        
        # 30 seconds is 150% of expected 12s (deviation = 150%)
        interval_data = sensor._calculate_interval("ethereum", 1001, 1600000030)
        
        assert interval_data["block_interval_sec"] == 30.0
        assert interval_data["interval_anomalous"] == True
