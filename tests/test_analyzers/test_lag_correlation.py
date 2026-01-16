"""Property-based tests for Lag-Correlation Analyzer.

Tests:
- Property 29: Lag range coverage - all lags from -max_lag to +max_lag tested
- Property 30: Optimal lag selection - optimal_lag corresponds to max correlation
- Property 31: Lag-correlation record completeness - all required fields present
- Property 32: Causal relationship flagging - abs(optimal_lag) > threshold flagged

Validates: Requirements 13.1, 13.2, 13.3, 13.4
"""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from src.analyzers.offline.lag_correlation import LagCorrelationAnalyzer


class TestLagCorrelationProperties:
    """Property-based tests for lag-correlation analysis."""
    
    @given(
        max_lag=st.integers(min_value=10, max_value=60),
        lag_step=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_property_29_lag_range_coverage(self, max_lag, lag_step):
        """Property 29: Lag range coverage.
        
        All lags from -max_lag to +max_lag are tested.
        """
        analyzer = LagCorrelationAnalyzer(max_lag=max_lag, lag_step=lag_step)
        
        # Create simple data
        n = 200
        np.random.seed(42)
        df = pd.DataFrame({
            "timestamp": np.arange(n),
            "a": np.random.randn(n),
            "b": np.random.randn(n)
        })
        
        result = analyzer.analyze_pair(df, "a", "b")
        correlations = result["all_correlations"]
        
        # Check all expected lags are present
        expected_lags = list(range(-max_lag, max_lag + 1, lag_step))
        actual_lags = [c["lag"] for c in correlations]
        
        assert set(expected_lags) == set(actual_lags)
    
    @given(
        n_samples=st.integers(min_value=100, max_value=300)
    )
    @settings(max_examples=100)
    def test_property_30_optimal_lag_selection(self, n_samples):
        """Property 30: Optimal lag selection.
        
        optimal_lag corresponds to maximum absolute correlation.
        """
        np.random.seed(42)
        df = pd.DataFrame({
            "timestamp": np.arange(n_samples),
            "a": np.random.randn(n_samples),
            "b": np.random.randn(n_samples)
        })
        
        analyzer = LagCorrelationAnalyzer(max_lag=30)
        result = analyzer.analyze_pair(df, "a", "b")
        
        correlations = result["all_correlations"]
        optimal_lag = result["optimal_lag"]
        max_corr = result["max_correlation"]
        
        # Find the correlation at optimal lag
        optimal_entry = next(c for c in correlations if c["lag"] == optimal_lag)
        
        # Verify it's the maximum
        max_abs_corr = max(abs(c["correlation"]) for c in correlations)
        assert abs(abs(optimal_entry["correlation"]) - max_abs_corr) < 1e-10
    
    @given(
        n_samples=st.integers(min_value=100, max_value=200)
    )
    @settings(max_examples=100)
    def test_property_31_record_completeness(self, n_samples):
        """Property 31: Lag-correlation record completeness.
        
        All required fields are present in results.
        """
        np.random.seed(42)
        df = pd.DataFrame({
            "timestamp": np.arange(n_samples),
            "a": np.random.randn(n_samples),
            "b": np.random.randn(n_samples)
        })
        
        analyzer = LagCorrelationAnalyzer()
        result = analyzer.analyze_pair(df, "a", "b")
        
        required_fields = [
            "param1", "param2", "optimal_lag", "max_correlation",
            "is_significant", "is_causal", "relationship", "all_correlations"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
    
    @given(
        causal_threshold=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100)
    def test_property_32_causal_flagging(self, causal_threshold):
        """Property 32: Causal relationship flagging.
        
        Pairs with abs(optimal_lag) > threshold are flagged as causal.
        """
        analyzer = LagCorrelationAnalyzer(
            causal_threshold=causal_threshold,
            min_correlation=0.0  # Accept any correlation for this test
        )
        
        # Create data with known lag
        n = 200
        np.random.seed(42)
        x = np.random.randn(n)
        
        # Create lagged version
        lag = causal_threshold + 5  # Definitely above threshold
        y = np.zeros(n)
        y[lag:] = x[:-lag]
        
        df = pd.DataFrame({
            "timestamp": np.arange(n),
            "a": x,
            "b": y
        })
        
        result = analyzer.analyze_pair(df, "a", "b")
        
        # If optimal lag exceeds threshold and correlation is significant
        if abs(result["optimal_lag"]) > causal_threshold and result["is_significant"]:
            assert result["is_causal"] == True


class TestLagCorrelationIntegration:
    """Integration tests for LagCorrelationAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return LagCorrelationAnalyzer(max_lag=30, causal_threshold=5)
    
    @pytest.fixture
    def sample_df(self):
        np.random.seed(42)
        n = 150
        x = np.random.randn(n)
        return pd.DataFrame({
            "timestamp": np.arange(n),
            "a": x,
            "b": np.roll(x, 10) + np.random.randn(n) * 0.1,  # Lagged by 10
            "c": np.random.randn(n)  # Independent
        })
    
    def test_analyze_all_pairs(self, analyzer, sample_df):
        """Analyzes all parameter pairs."""
        results = analyzer.analyze_all_pairs(sample_df)
        
        # Should have 3 pairs: (a,b), (a,c), (b,c)
        assert len(results) == 3
    
    def test_get_causal_relationships(self, analyzer, sample_df):
        """Filters to causal relationships."""
        all_results = analyzer.analyze_all_pairs(sample_df)
        causal = analyzer.get_causal_relationships(all_results)
        
        for result in causal:
            assert result["is_causal"] == True
    
    def test_full_analyze(self, analyzer, sample_df):
        """Full analysis returns expected structure."""
        results = analyzer.analyze(sample_df)
        
        assert "all_pairs" in results
        assert "causal_relationships" in results
        assert "total_pairs" in results
        assert "causal_count" in results
        assert "max_lag_tested" in results
    
    def test_missing_column(self, analyzer, sample_df):
        """Handles missing column gracefully."""
        result = analyzer.analyze_pair(sample_df, "a", "nonexistent")
        
        assert "error" in result
    
    def test_relationship_description(self, analyzer):
        """Relationship description is correct."""
        n = 150
        np.random.seed(42)
        x = np.random.randn(n)
        
        df = pd.DataFrame({
            "timestamp": np.arange(n),
            "leader": x,
            "follower": np.roll(x, 15)  # Follower lags by 15
        })
        
        result = analyzer.analyze_pair(df, "leader", "follower")
        
        # The relationship should indicate leader leads follower
        assert "leads" in result["relationship"] or "Simultaneous" in result["relationship"]
