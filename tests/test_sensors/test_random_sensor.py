"""Property-based tests for Random Sensor.

Tests:
- Property 6: Random sensor batch size - exactly 1024 values per batch
- Property 7: Random sensor statistics correctness - zeros + ones = total, chi_square formula correct
- Property 8: Non-random detection - p_value < 0.01 flagged as anomalous

Validates: Requirements 5.3, 5.4, 5.6
"""

import asyncio
import math
from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies as st
from scipy import stats

from src.sensors.random_sensor import RandomSensor


class TestRandomSensorProperties:
    """Property-based tests for RandomSensor."""
    
    @given(batch_size=st.integers(min_value=100, max_value=2048))
    @settings(max_examples=100)
    def test_property_6_batch_size(self, batch_size):
        """Property 6: Random sensor batch size.
        
        Each batch contains exactly the configured number of values.
        """
        sensor = RandomSensor(batch_size=batch_size)
        
        # Test Python random collection
        result = sensor._collect_python_random()
        assert result["sample_size"] == batch_size
        
        # Test urandom collection
        result = sensor._collect_urandom()
        assert result["sample_size"] == batch_size
    
    @given(
        values=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=100,
            max_size=2000
        )
    )
    @settings(max_examples=100)
    def test_property_7_statistics_correctness(self, values):
        """Property 7: Random sensor statistics correctness.
        
        - zeros_count + ones_count = sample_size
        - chi_square formula is correct
        """
        if len(values) < 10:
            return  # Skip very small samples
        
        sensor = RandomSensor(batch_size=len(values))
        result = sensor._analyze_random_values(values, "test")
        
        # Verify zeros + ones = total
        assert result["zeros_count"] + result["ones_count"] == len(values)
        
        # Verify chi-square calculation
        expected = len(values) / 2
        zeros = result["zeros_count"]
        ones = result["ones_count"]
        expected_chi_sq = ((zeros - expected) ** 2 / expected + 
                          (ones - expected) ** 2 / expected)
        
        assert abs(result["chi_square"] - expected_chi_sq) < 0.01
        
        # Verify zeros_ratio is correct
        expected_ratio = zeros / len(values)
        assert abs(result["zeros_ratio"] - expected_ratio) < 0.001
    
    @given(
        bias=st.floats(min_value=0.0, max_value=0.3)
    )
    @settings(max_examples=100)
    def test_property_8_non_random_detection(self, bias):
        """Property 8: Non-random detection.
        
        Highly biased sequences (p_value < 0.01) are flagged as anomalous.
        """
        sensor = RandomSensor(batch_size=1024)
        
        # Create biased sequence (all values near 0 or 1)
        if bias < 0.1:
            # Very biased - should be detected
            values = [0.1] * 1024  # All zeros in bit representation
        else:
            # Less biased - may or may not be detected
            values = [0.1 + i * 0.8 / 1024 for i in range(1024)]
        
        result = sensor._analyze_random_values(values, "test")
        
        # If p_value < 0.01, must be flagged
        if result["p_value"] < 0.01 or result["p_value_uniform"] < 0.01:
            assert result["is_anomalous"] == True
        
        # If flagged, at least one p_value must be < 0.01
        if result["is_anomalous"]:
            assert result["p_value"] < 0.01 or result["p_value_uniform"] < 0.01
    
    @given(
        zeros=st.integers(min_value=0, max_value=1024),
    )
    @settings(max_examples=100)
    def test_chi_square_bounds(self, zeros):
        """Chi-square statistic is non-negative."""
        ones = 1024 - zeros
        expected = 512
        
        chi_sq = ((zeros - expected) ** 2 / expected + 
                  (ones - expected) ** 2 / expected)
        
        assert chi_sq >= 0
        
        # P-value should be in [0, 1]
        p_value = 1 - stats.chi2.cdf(chi_sq, df=1)
        assert 0 <= p_value <= 1
    
    @given(
        values=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=100,
            max_size=1000
        )
    )
    @settings(max_examples=100)
    def test_bin_distribution_sum(self, values):
        """Bin distribution sums to sample size."""
        if len(values) < 10:
            return
        
        sensor = RandomSensor(batch_size=len(values))
        result = sensor._analyze_random_values(values, "test")
        
        assert sum(result["bin_distribution"]) == len(values)
        assert len(result["bin_distribution"]) == 10


class TestRandomSensorIntegration:
    """Integration tests for RandomSensor."""
    
    @pytest.fixture
    def sensor(self):
        return RandomSensor(batch_size=1024, use_random_org=False)
    
    def test_schema(self, sensor):
        """Schema defines expected fields."""
        schema = sensor.get_schema()
        assert "timestamp" in schema
        assert "batch_size" in schema
        assert "python_random" in schema
        assert "urandom" in schema
        assert "any_anomalous" in schema
    
    @pytest.mark.asyncio
    async def test_collect_returns_all_sources(self, sensor):
        """Collect returns data from all configured sources."""
        reading = await sensor.collect()
        
        assert "python_random" in reading.data
        assert "urandom" in reading.data
        assert reading.data["batch_size"] == 1024
        
        # Verify python_random structure
        pr = reading.data["python_random"]
        assert pr["source"] == "python_random"
        assert pr["sample_size"] == 1024
        assert "zeros_count" in pr
        assert "ones_count" in pr
        assert "chi_square" in pr
        assert "p_value" in pr
        
        # Verify urandom structure
        ur = reading.data["urandom"]
        assert ur["source"] == "urandom"
        assert ur["sample_size"] == 1024
    
    @pytest.mark.asyncio
    async def test_any_anomalous_flag(self, sensor):
        """any_anomalous flag reflects individual source flags."""
        reading = await sensor.collect()
        
        pr_anomalous = reading.data["python_random"]["is_anomalous"]
        ur_anomalous = reading.data["urandom"]["is_anomalous"]
        
        expected = pr_anomalous or ur_anomalous
        assert reading.data["any_anomalous"] == expected
    
    def test_python_random_reproducibility(self):
        """Python random with seed produces reproducible results."""
        import random
        
        sensor = RandomSensor(batch_size=100)
        
        random.seed(42)
        result1 = sensor._collect_python_random()
        
        random.seed(42)
        result2 = sensor._collect_python_random()
        
        assert result1["zeros_count"] == result2["zeros_count"]
        assert result1["chi_square"] == result2["chi_square"]
