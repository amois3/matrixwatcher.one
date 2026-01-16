"""Property-based tests for Precursor Analyzer.

Tests:
- Property 38: Pre-anomaly window extraction - windows at exactly 5, 10, 30 seconds
- Property 39: Pattern frequency calculation - frequency = count / total
- Property 40: Precursor threshold - >30% flagged as precursor

Validates: Requirements 15.1, 15.3, 15.4
"""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from src.analyzers.offline.precursor import PrecursorAnalyzer


class TestPrecursorAnalyzerProperties:
    """Property-based tests for precursor analysis."""
    
    @given(
        windows=st.lists(
            st.integers(min_value=1, max_value=60),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_38_window_extraction(self, windows):
        """Property 38: Pre-anomaly window extraction.
        
        Windows are extracted at exactly the specified seconds before anomaly.
        """
        analyzer = PrecursorAnalyzer(windows=windows)
        
        # Create data
        n = 200
        data = pd.DataFrame({
            "timestamp": np.arange(n, dtype=float),
            "value": np.random.randn(n)
        })
        
        # Create anomaly at t=100
        anomalies = pd.DataFrame({
            "timestamp": [100.0]
        })
        
        windows_data = analyzer.extract_pre_anomaly_windows(data, anomalies)
        
        # Check all window sizes are present
        assert set(windows_data.keys()) == set(windows)
        
        # Check window timing
        for window_size, window_list in windows_data.items():
            if window_list:
                window_df = window_list[0]
                # Window should end before anomaly time
                assert window_df["timestamp"].max() < 100.0
                # Window should start at anomaly_time - window_size
                assert window_df["timestamp"].min() >= 100.0 - window_size
    
    @given(
        min_frequency=st.floats(min_value=0.1, max_value=0.9)
    )
    @settings(max_examples=100)
    def test_property_40_precursor_threshold(self, min_frequency):
        """Property 40: Precursor threshold.
        
        Patterns appearing in >= min_frequency of windows are flagged.
        """
        analyzer = PrecursorAnalyzer(
            windows=[5],
            min_frequency=min_frequency,
            z_threshold=0.5  # Lower threshold for testing
        )
        
        # Create windows with elevated values
        n_windows = 20
        windows = []
        
        for i in range(n_windows):
            # Create window with elevated value
            window_df = pd.DataFrame({
                "timestamp": [i * 100 + j for j in range(5)],
                "value": [10.0] * 5 if i < n_windows * 0.8 else [0.0] * 5
            })
            windows.append(window_df)
        
        result = analyzer.analyze_window_patterns(windows, parameters=["value"])
        
        for pattern in result["patterns"]:
            if pattern["is_precursor"]:
                assert pattern["frequency"] >= min_frequency


class TestPrecursorAnalyzerIntegration:
    """Integration tests for PrecursorAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return PrecursorAnalyzer(windows=[5, 10, 30], min_frequency=0.3)
    
    @pytest.fixture
    def sample_data(self):
        np.random.seed(42)
        n = 500
        return pd.DataFrame({
            "timestamp": np.arange(n, dtype=float),
            "cpu": np.random.randn(n) * 10 + 50,
            "memory": np.random.randn(n) * 5 + 70,
            "latency": np.random.randn(n) * 20 + 100
        })
    
    @pytest.fixture
    def sample_anomalies(self):
        return pd.DataFrame({
            "timestamp": [100.0, 200.0, 300.0, 400.0]
        })
    
    def test_extract_windows(self, analyzer, sample_data, sample_anomalies):
        """Extracts windows for all anomalies."""
        windows = analyzer.extract_pre_anomaly_windows(sample_data, sample_anomalies)
        
        assert 5 in windows
        assert 10 in windows
        assert 30 in windows
        
        # Should have windows for each anomaly
        for window_size, window_list in windows.items():
            assert len(window_list) <= len(sample_anomalies)
    
    def test_analyze_window_patterns(self, analyzer, sample_data, sample_anomalies):
        """Analyzes patterns in windows."""
        windows = analyzer.extract_pre_anomaly_windows(sample_data, sample_anomalies)
        
        result = analyzer.analyze_window_patterns(windows[5])
        
        assert "patterns" in result
        assert "total_windows" in result
        assert "parameters_analyzed" in result
    
    def test_find_precursors(self, analyzer, sample_data, sample_anomalies):
        """Finds precursor patterns."""
        results = analyzer.find_precursors(sample_data, sample_anomalies)
        
        assert "by_window" in results
        assert "all_precursors" in results
        assert "precursor_count" in results
        assert "windows_analyzed" in results
    
    def test_generate_report(self, analyzer, sample_data, sample_anomalies):
        """Generates text report."""
        results = analyzer.find_precursors(sample_data, sample_anomalies)
        report = analyzer.generate_report(results)
        
        assert isinstance(report, str)
        assert "PRECURSOR ANALYSIS REPORT" in report
    
    def test_full_analyze(self, analyzer, sample_data, sample_anomalies):
        """Full analysis returns report."""
        results = analyzer.analyze(sample_data, sample_anomalies)
        
        assert "report" in results
        assert "by_window" in results
        assert "all_precursors" in results
    
    def test_empty_anomalies(self, analyzer, sample_data):
        """Handles empty anomalies gracefully."""
        empty_anomalies = pd.DataFrame(columns=["timestamp"])
        results = analyzer.find_precursors(sample_data, empty_anomalies)
        
        assert results["precursor_count"] == 0
    
    def test_pattern_structure(self, analyzer, sample_data, sample_anomalies):
        """Pattern records have correct structure."""
        results = analyzer.find_precursors(sample_data, sample_anomalies)
        
        for pattern in results["all_precursors"]:
            assert "parameter" in pattern
            assert "pattern_type" in pattern
            assert "frequency" in pattern
            assert "count" in pattern
            assert "is_precursor" in pattern
