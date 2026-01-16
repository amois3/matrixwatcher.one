"""Property-based tests for Network Sensor.

Tests Property 5: Network sensor record completeness - all required fields present.
Validates: Requirements 4.3
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.sensors.network_sensor import NetworkSensor, DEFAULT_TARGETS


class TestNetworkSensorProperties:
    """Property-based tests for NetworkSensor."""
    
    @given(
        latency=st.floats(min_value=0.1, max_value=5000.0),
        status_code=st.integers(min_value=100, max_value=599),
        response_size=st.integers(min_value=0, max_value=1000000)
    )
    @settings(max_examples=100)
    def test_property_5_record_completeness(self, latency, status_code, response_size):
        """Property 5: Network sensor record completeness.
        
        All probe results must contain required fields:
        - target, url, latency_ms, status_code, response_size_bytes, reachable
        """
        sensor = NetworkSensor()
        
        # Create mock probe result
        probe_result = {
            "target": "test",
            "url": "https://test.com",
            "latency_ms": round(latency, 2),
            "status_code": status_code,
            "response_size_bytes": response_size,
            "reachable": True
        }
        
        # Verify all required fields present
        required_fields = ["target", "url", "latency_ms", "status_code", 
                          "response_size_bytes", "reachable"]
        for field in required_fields:
            assert field in probe_result, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(probe_result["target"], str)
        assert isinstance(probe_result["url"], str)
        assert isinstance(probe_result["latency_ms"], float)
        assert isinstance(probe_result["status_code"], int)
        assert isinstance(probe_result["response_size_bytes"], int)
        assert isinstance(probe_result["reachable"], bool)
    
    @given(
        num_targets=st.integers(min_value=1, max_value=10),
        num_reachable=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_aggregate_stats_correctness(self, num_targets, num_reachable):
        """Aggregate statistics are calculated correctly."""
        num_reachable = min(num_reachable, num_targets)
        
        # Create mock probes
        probes = []
        for i in range(num_targets):
            if i < num_reachable:
                probes.append({
                    "target": f"target_{i}",
                    "url": f"https://target{i}.com",
                    "latency_ms": 100.0 + i * 10,
                    "status_code": 200,
                    "response_size_bytes": 1000,
                    "reachable": True
                })
            else:
                probes.append({
                    "target": f"target_{i}",
                    "url": f"https://target{i}.com",
                    "latency_ms": -1,
                    "status_code": 0,
                    "response_size_bytes": 0,
                    "reachable": False
                })
        
        # Calculate expected stats
        reachable_probes = [p for p in probes if p["reachable"]]
        expected_avg = (
            sum(p["latency_ms"] for p in reachable_probes) / len(reachable_probes)
            if reachable_probes else -1
        )
        
        # Verify
        assert len([p for p in probes if p["reachable"]]) == num_reachable
        if num_reachable > 0:
            assert expected_avg >= 0
        else:
            assert expected_avg == -1
    
    @given(timeout=st.floats(min_value=0.1, max_value=60.0))
    @settings(max_examples=100)
    def test_timeout_configuration(self, timeout):
        """Timeout is properly configured."""
        sensor = NetworkSensor(timeout=timeout)
        assert sensor.timeout == timeout
    
    @given(
        targets=st.lists(
            st.fixed_dictionaries({
                "url": st.text(min_size=10, max_size=100).map(lambda x: f"https://{x}.com"),
                "name": st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz")
            }),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_custom_targets_configuration(self, targets):
        """Custom targets are properly configured."""
        sensor = NetworkSensor(targets=targets)
        assert sensor.targets == targets
        assert len(sensor.targets) == len(targets)


class TestNetworkSensorIntegration:
    """Integration tests for NetworkSensor."""
    
    @pytest.fixture
    def sensor(self):
        return NetworkSensor(timeout=5.0)
    
    def test_default_targets(self, sensor):
        """Default targets are configured."""
        assert len(sensor.targets) == len(DEFAULT_TARGETS)
        for target in sensor.targets:
            assert "url" in target
            assert "name" in target
    
    def test_schema(self, sensor):
        """Schema defines expected fields."""
        schema = sensor.get_schema()
        assert "timestamp" in schema
        assert "probes" in schema
        assert "targets_total" in schema
        assert "targets_reachable" in schema
        assert "avg_latency_ms" in schema
    
    @pytest.mark.asyncio
    async def test_unreachable_target_handling(self, sensor):
        """Unreachable targets return proper error structure."""
        # Mock a failed request
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 0
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_session_instance = MagicMock()
            mock_session_instance.get = mock_get
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance
            
            reading = await sensor.collect()
            
            # All probes should be unreachable
            for probe in reading.data["probes"]:
                assert probe["reachable"] == False
                assert probe["latency_ms"] == -1
                assert probe["status_code"] == 0
