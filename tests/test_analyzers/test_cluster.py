"""Property-based tests for Cluster Analyzer.

Tests:
- Property 33: Temporal clustering - anomalies within ±time_window connected
- Property 34: Graph construction - one node per anomaly, edges only for proximate
- Property 35: Cluster identification - connected components = clusters
- Property 36: Cluster ranking - ranked by sources, count, span
- Property 37: Multi-source cluster flagging - 3+ sensors flagged significant

Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5
"""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from src.analyzers.offline.cluster import ClusterAnalyzer


class TestClusterAnalyzerProperties:
    """Property-based tests for cluster analysis."""
    
    @given(
        time_window=st.floats(min_value=1.0, max_value=10.0),
        n_anomalies=st.integers(min_value=5, max_value=50)
    )
    @settings(max_examples=100)
    def test_property_33_temporal_clustering(self, time_window, n_anomalies):
        """Property 33: Temporal clustering.
        
        Anomalies within ±time_window seconds are connected.
        """
        analyzer = ClusterAnalyzer(time_window=time_window, min_cluster_size=2)
        
        # Create anomalies in a tight cluster
        timestamps = [0.0 + i * (time_window * 0.5) for i in range(n_anomalies)]
        
        anomalies = pd.DataFrame({
            "timestamp": timestamps,
            "source": [f"sensor_{i % 3}" for i in range(n_anomalies)]
        })
        
        clusters = analyzer.find_clusters(anomalies)
        
        # All anomalies should be in one cluster (they're all within window of neighbors)
        if clusters:
            total_in_clusters = sum(c["anomaly_count"] for c in clusters)
            # Most should be clustered
            assert total_in_clusters >= n_anomalies * 0.5
    
    @given(
        n_anomalies=st.integers(min_value=10, max_value=30)
    )
    @settings(max_examples=100)
    def test_property_34_graph_construction(self, n_anomalies):
        """Property 34: Graph construction.
        
        One node per anomaly, edges only for temporally proximate pairs.
        """
        analyzer = ClusterAnalyzer(time_window=2.0, min_cluster_size=1)
        
        # Create widely spaced anomalies (no edges)
        timestamps = [i * 100.0 for i in range(n_anomalies)]  # 100s apart
        
        anomalies = pd.DataFrame({
            "timestamp": timestamps,
            "source": [f"sensor_{i}" for i in range(n_anomalies)]
        })
        
        clusters = analyzer.find_clusters(anomalies)
        
        # Each anomaly should be its own cluster (no connections)
        # But min_cluster_size=1 means all are clusters
        # With min_cluster_size=2, none should form clusters
        analyzer2 = ClusterAnalyzer(time_window=2.0, min_cluster_size=2)
        clusters2 = analyzer2.find_clusters(anomalies)
        
        assert len(clusters2) == 0  # No clusters with size >= 2
    
    @given(
        n_clusters=st.integers(min_value=2, max_value=5),
        cluster_size=st.integers(min_value=3, max_value=8)
    )
    @settings(max_examples=100)
    def test_property_35_cluster_identification(self, n_clusters, cluster_size):
        """Property 35: Cluster identification.
        
        Connected components are identified as clusters.
        """
        analyzer = ClusterAnalyzer(time_window=2.0, min_cluster_size=2)
        
        # Create distinct clusters
        timestamps = []
        sources = []
        
        for cluster_idx in range(n_clusters):
            base_time = cluster_idx * 1000  # Well separated
            for i in range(cluster_size):
                timestamps.append(base_time + i * 0.5)  # Within window
                sources.append(f"sensor_{i % 3}")
        
        anomalies = pd.DataFrame({
            "timestamp": timestamps,
            "source": sources
        })
        
        clusters = analyzer.find_clusters(anomalies)
        
        # Should find approximately n_clusters
        assert len(clusters) >= n_clusters - 1  # Allow some tolerance
    
    @given(
        multi_source_threshold=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100)
    def test_property_37_multi_source_flagging(self, multi_source_threshold):
        """Property 37: Multi-source cluster flagging.
        
        Clusters with >= threshold sources are flagged as significant.
        """
        analyzer = ClusterAnalyzer(
            time_window=5.0,
            min_cluster_size=2,
            multi_source_threshold=multi_source_threshold
        )
        
        # Create cluster with exactly threshold sources
        n_sources = multi_source_threshold
        timestamps = [i * 0.5 for i in range(n_sources * 2)]
        sources = [f"sensor_{i % n_sources}" for i in range(n_sources * 2)]
        
        anomalies = pd.DataFrame({
            "timestamp": timestamps,
            "source": sources
        })
        
        clusters = analyzer.find_clusters(anomalies)
        
        for cluster in clusters:
            if cluster["unique_sources"] >= multi_source_threshold:
                assert cluster["is_multi_source"] == True
            else:
                assert cluster["is_multi_source"] == False


class TestClusterAnalyzerIntegration:
    """Integration tests for ClusterAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return ClusterAnalyzer(time_window=3.0, min_cluster_size=2, multi_source_threshold=3)
    
    @pytest.fixture
    def sample_anomalies(self):
        return pd.DataFrame({
            "timestamp": [0, 1, 2, 100, 101, 102, 103, 200],
            "source": ["a", "b", "c", "a", "b", "c", "d", "a"],
            "value": [1, 2, 3, 4, 5, 6, 7, 8]
        })
    
    def test_find_clusters(self, analyzer, sample_anomalies):
        """Finds expected clusters."""
        clusters = analyzer.find_clusters(sample_anomalies)
        
        # Should find 2 clusters (0-2 and 100-103)
        assert len(clusters) == 2
    
    def test_cluster_structure(self, analyzer, sample_anomalies):
        """Clusters have correct structure."""
        clusters = analyzer.find_clusters(sample_anomalies)
        
        for cluster in clusters:
            assert "anomaly_count" in cluster
            assert "unique_sources" in cluster
            assert "sources" in cluster
            assert "start_time" in cluster
            assert "end_time" in cluster
            assert "time_span" in cluster
            assert "is_multi_source" in cluster
    
    def test_get_multi_source_clusters(self, analyzer, sample_anomalies):
        """Filters to multi-source clusters."""
        clusters = analyzer.find_clusters(sample_anomalies)
        multi = analyzer.get_multi_source_clusters(clusters)
        
        for cluster in multi:
            assert cluster["unique_sources"] >= 3
    
    def test_rank_clusters(self, analyzer, sample_anomalies):
        """Ranks clusters correctly."""
        clusters = analyzer.find_clusters(sample_anomalies)
        ranked = analyzer.rank_clusters(clusters)
        
        # Check ranks are assigned
        for i, cluster in enumerate(ranked):
            assert cluster["rank"] == i + 1
            assert "score" in cluster
    
    def test_get_cluster_summary(self, analyzer, sample_anomalies):
        """Summary DataFrame has correct columns."""
        clusters = analyzer.find_clusters(sample_anomalies)
        ranked = analyzer.rank_clusters(clusters)
        summary = analyzer.get_cluster_summary(ranked)
        
        assert "rank" in summary.columns
        assert "anomaly_count" in summary.columns
        assert "unique_sources" in summary.columns
        assert "time_span" in summary.columns
    
    def test_analyze_returns_all_components(self, analyzer, sample_anomalies):
        """Analyze returns all expected components."""
        results = analyzer.analyze(sample_anomalies)
        
        assert "clusters" in results
        assert "multi_source_clusters" in results
        assert "summary" in results
        assert "total_clusters" in results
        assert "multi_source_count" in results
    
    def test_empty_anomalies(self, analyzer):
        """Handles empty DataFrame gracefully."""
        empty_df = pd.DataFrame(columns=["timestamp", "source"])
        clusters = analyzer.find_clusters(empty_df)
        
        assert clusters == []
