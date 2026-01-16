"""Property-based tests for Correlation Analyzer.

Tests:
- Property 26: Correlation matrix symmetry - corr(A,B) = corr(B,A)
- Property 27: Pearson correlation bounds - values in [-1, 1]
- Property 28: Significant correlation filtering - all pairs in list have abs > threshold

Validates: Requirements 12.1, 12.2, 12.4
"""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from src.analyzers.offline.correlation import CorrelationAnalyzer


class TestCorrelationMatrixProperties:
    """Property-based tests for correlation matrix."""
    
    @given(
        n_rows=st.integers(min_value=50, max_value=200),
        n_cols=st.integers(min_value=3, max_value=10)
    )
    @settings(max_examples=100)
    def test_property_26_matrix_symmetry(self, n_rows, n_cols):
        """Property 26: Correlation matrix symmetry.
        
        corr(A, B) = corr(B, A) for all parameter pairs.
        """
        # Generate random data
        np.random.seed(42)
        data = {f"col_{i}": np.random.randn(n_rows) for i in range(n_cols)}
        df = pd.DataFrame(data)
        
        analyzer = CorrelationAnalyzer()
        matrix = analyzer.compute_matrix(df)
        
        # Check symmetry
        for i, col1 in enumerate(matrix.columns):
            for j, col2 in enumerate(matrix.columns):
                assert abs(matrix.loc[col1, col2] - matrix.loc[col2, col1]) < 1e-10
    
    @given(
        n_rows=st.integers(min_value=50, max_value=200),
        n_cols=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=100)
    def test_property_27_correlation_bounds(self, n_rows, n_cols):
        """Property 27: Pearson correlation bounds.
        
        All correlation values must be in [-1, 1].
        """
        np.random.seed(42)
        data = {f"col_{i}": np.random.randn(n_rows) for i in range(n_cols)}
        df = pd.DataFrame(data)
        
        analyzer = CorrelationAnalyzer()
        matrix = analyzer.compute_matrix(df)
        
        # Check bounds
        for col1 in matrix.columns:
            for col2 in matrix.columns:
                val = matrix.loc[col1, col2]
                if not np.isnan(val):
                    assert -1.0 <= val <= 1.0
    
    @given(
        threshold=st.floats(min_value=0.1, max_value=0.9)
    )
    @settings(max_examples=100)
    def test_property_28_significant_filtering(self, threshold):
        """Property 28: Significant correlation filtering.
        
        All pairs in significant list have abs(correlation) >= threshold.
        """
        np.random.seed(42)
        # Create data with some correlated columns
        n = 100
        x = np.random.randn(n)
        data = {
            "a": x,
            "b": x + np.random.randn(n) * 0.1,  # Highly correlated
            "c": np.random.randn(n),  # Independent
            "d": -x + np.random.randn(n) * 0.1,  # Negatively correlated
        }
        df = pd.DataFrame(data)
        
        analyzer = CorrelationAnalyzer(significance_threshold=threshold)
        matrix = analyzer.compute_matrix(df)
        significant = analyzer.get_significant_pairs(matrix)
        
        # All significant pairs must exceed threshold
        for pair in significant:
            assert pair["abs_correlation"] >= threshold


class TestCorrelationAnalyzerIntegration:
    """Integration tests for CorrelationAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return CorrelationAnalyzer(significance_threshold=0.7, min_samples=30)
    
    @pytest.fixture
    def sample_df(self):
        np.random.seed(42)
        n = 100
        x = np.random.randn(n)
        return pd.DataFrame({
            "a": x,
            "b": x * 0.9 + np.random.randn(n) * 0.1,
            "c": np.random.randn(n),
            "d": -x * 0.8 + np.random.randn(n) * 0.2,
        })
    
    def test_compute_matrix_shape(self, analyzer, sample_df):
        """Matrix has correct shape."""
        matrix = analyzer.compute_matrix(sample_df)
        assert matrix.shape == (4, 4)
    
    def test_diagonal_is_one(self, analyzer, sample_df):
        """Diagonal elements are 1.0."""
        matrix = analyzer.compute_matrix(sample_df)
        for col in matrix.columns:
            assert abs(matrix.loc[col, col] - 1.0) < 1e-10
    
    def test_significant_pairs_structure(self, analyzer, sample_df):
        """Significant pairs have correct structure."""
        matrix = analyzer.compute_matrix(sample_df)
        pairs = analyzer.get_significant_pairs(matrix)
        
        for pair in pairs:
            assert "param1" in pair
            assert "param2" in pair
            assert "correlation" in pair
            assert "abs_correlation" in pair
            assert "direction" in pair
    
    def test_compute_with_pvalues(self, analyzer, sample_df):
        """P-values are computed correctly."""
        corr, pval = analyzer.compute_with_pvalues(sample_df)
        
        assert corr.shape == pval.shape
        
        # P-values should be in [0, 1]
        for col1 in pval.columns:
            for col2 in pval.columns:
                val = pval.loc[col1, col2]
                if not np.isnan(val):
                    assert 0.0 <= val <= 1.0
    
    def test_analyze_returns_all_components(self, analyzer, sample_df):
        """Analyze returns all expected components."""
        results = analyzer.analyze(sample_df)
        
        assert "correlation_matrix" in results
        assert "pvalue_matrix" in results
        assert "significant_pairs" in results
        assert "total_parameters" in results
        assert "significant_count" in results
    
    def test_insufficient_samples(self, analyzer):
        """Handles insufficient samples gracefully."""
        small_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        matrix = analyzer.compute_matrix(small_df)
        
        assert matrix.empty
    
    def test_single_column(self, analyzer):
        """Handles single column gracefully."""
        single_df = pd.DataFrame({"a": np.random.randn(100)})
        matrix = analyzer.compute_matrix(single_df)
        
        assert matrix.empty
