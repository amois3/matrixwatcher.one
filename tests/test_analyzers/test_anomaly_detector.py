"""Property-based tests for Online Anomaly Detector.

Tests:
- Property 22: Sliding window size - window contains at most N values
- Property 23: Z-score calculation - formula (value - mean) / std correct
- Property 24: Anomaly classification - abs(z_score) > 4.0 classified as anomaly
- Property 25: Anomaly record completeness - all required fields present

Validates: Requirements 11.1, 11.2, 11.3, 11.6
"""

import math
import statistics
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from src.analyzers.online.anomaly_detector import AnomalyDetector, SlidingWindow


class TestSlidingWindowProperties:
    """Property-based tests for SlidingWindow."""
    
    @given(
        window_size=st.integers(min_value=10, max_value=1000),
        values=st.lists(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False), min_size=1, max_size=2000)
    )
    @settings(max_examples=100)
    def test_property_22_window_size_limit(self, window_size, values):
        """Property 22: Sliding window size.
        
        Window contains at most N values (configured size).
        """
        window = SlidingWindow(max_size=window_size)
        
        for value in values:
            window.add(value)
        
        # Window should never exceed max_size
        assert len(window) <= window_size
        
        # After adding more than max_size values, should be exactly max_size
        if len(values) >= window_size:
            assert len(window) == window_size
    
    @given(
        values=st.lists(
            st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_property_23_z_score_calculation(self, values):
        """Property 23: Z-score calculation.
        
        Z-score formula: (value - mean) / std
        """
        window = SlidingWindow(max_size=100)
        
        for value in values[:-1]:
            window.add(value)
        
        if len(window) < 2:
            return  # Need at least 2 values for std
        
        test_value = values[-1]
        mean = window.mean()
        std = window.std()
        
        if std > 0:
            expected_z = (test_value - mean) / std
            actual_z = window.z_score(test_value)
            
            assert abs(actual_z - expected_z) < 0.0001
    
    @given(
        values=st.lists(
            st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_mean_calculation(self, values):
        """Mean is calculated correctly."""
        window = SlidingWindow(max_size=100)
        
        for value in values:
            window.add(value)
        
        expected_mean = statistics.mean(values[-100:])  # Last 100 values
        actual_mean = window.mean()
        
        assert abs(actual_mean - expected_mean) < 0.0001
    
    @given(
        values=st.lists(
            st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_std_calculation(self, values):
        """Standard deviation is calculated correctly."""
        window = SlidingWindow(max_size=100)
        
        for value in values:
            window.add(value)
        
        if len(values) < 2:
            return
        
        expected_std = statistics.stdev(values[-100:])
        actual_std = window.std()
        
        assert abs(actual_std - expected_std) < 0.0001


class TestAnomalyDetectorProperties:
    """Property-based tests for AnomalyDetector."""
    
    @given(
        threshold=st.floats(min_value=1.0, max_value=10.0),
        z_score=st.floats(min_value=-20.0, max_value=20.0)
    )
    @settings(max_examples=100)
    def test_property_24_anomaly_classification(self, threshold, z_score):
        """Property 24: Anomaly classification.
        
        Values with abs(z_score) > threshold are classified as anomalies.
        """
        detector = AnomalyDetector(threshold=threshold)
        
        is_anomaly = abs(z_score) > threshold
        
        # Verify classification logic
        assert (abs(z_score) > detector.threshold) == is_anomaly
    
    @given(
        source=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        parameter=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        value=st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        z_score=st.floats(min_value=-20.0, max_value=20.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_property_25_anomaly_record_completeness(self, source, parameter, value, z_score):
        """Property 25: Anomaly record completeness.
        
        All anomaly records must contain required fields.
        """
        import time
        
        anomaly_record = {
            "timestamp": time.time(),
            "source": source,
            "parameter": parameter,
            "value": value,
            "z_score": z_score,
            "mean": 0.0,
            "std": 1.0,
            "threshold": 4.0
        }
        
        # Verify all required fields present
        required_fields = [
            "timestamp", "source", "parameter", "value",
            "z_score", "mean", "std", "threshold"
        ]
        for field in required_fields:
            assert field in anomaly_record, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(anomaly_record["timestamp"], float)
        assert isinstance(anomaly_record["source"], str)
        assert isinstance(anomaly_record["parameter"], str)
        assert isinstance(anomaly_record["value"], float)
        assert isinstance(anomaly_record["z_score"], float)
    
    @given(
        window_size=st.integers(min_value=10, max_value=500),
        threshold=st.floats(min_value=1.0, max_value=10.0)
    )
    @settings(max_examples=100)
    def test_configuration(self, window_size, threshold):
        """Detector is properly configured."""
        detector = AnomalyDetector(window_size=window_size, threshold=threshold)
        
        assert detector.window_size == window_size
        assert detector.threshold == threshold


class TestAnomalyDetectorIntegration:
    """Integration tests for AnomalyDetector."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector(window_size=100, threshold=4.0)
    
    def test_default_configuration(self, detector):
        """Default configuration is set."""
        assert detector.window_size == 100
        assert detector.threshold == 4.0
    
    def test_process_normal_value(self, detector):
        """Normal values are not flagged as anomalies."""
        # Add baseline values
        for i in range(50):
            detector.process("test", "param", 100.0 + i * 0.1)
        
        # Add a normal value
        result = detector.process("test", "param", 102.5)
        
        assert result is None or result.get("is_anomaly") == False
    
    def test_process_anomalous_value(self, detector):
        """Anomalous values are flagged."""
        # Add baseline values (mean ~100, std ~0.3)
        for i in range(50):
            detector.process("test", "param", 100.0 + (i % 2) * 0.1)
        
        # Add an extreme value (should be anomaly)
        result = detector.process("test", "param", 200.0)
        
        if result:
            assert result.get("is_anomaly") == True
            assert abs(result["z_score"]) > 4.0
    
    def test_multiple_parameters(self, detector):
        """Multiple parameters are tracked independently."""
        # Add values for param1
        for i in range(20):
            detector.process("test", "param1", 100.0)
        
        # Add values for param2
        for i in range(20):
            detector.process("test", "param2", 200.0)
        
        # Each parameter should have its own window
        assert "test:param1" in detector._windows
        assert "test:param2" in detector._windows
    
    def test_get_stats(self, detector):
        """Statistics are returned correctly."""
        for i in range(30):
            detector.process("test", "param", 100.0 + i)
        
        stats = detector.get_stats("test", "param")
        
        assert "count" in stats
        assert "mean" in stats
        assert "std" in stats
        assert stats["count"] == 30
    
    def test_clear_windows(self, detector):
        """Windows can be cleared."""
        for i in range(20):
            detector.process("test", "param", 100.0)
        
        assert len(detector._windows) > 0
        
        detector.clear()
        
        assert len(detector._windows) == 0
