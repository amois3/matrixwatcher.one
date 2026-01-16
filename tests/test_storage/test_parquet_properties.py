"""Property-based tests for Parquet export.

Feature: matrix-watcher, Property 19: Parquet export round-trip
Validates: Requirements 10.5
"""

import pytest
import tempfile
import os
from hypothesis import given, strategies as st, settings, HealthCheck

from src.storage.parquet_export import ParquetExporter, export_to_parquet, import_from_parquet


# Simplified strategies
simple_text = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
timestamp_strategy = st.floats(min_value=1000000000, max_value=2000000000, allow_nan=False, allow_infinity=False)


# ============================================================================
# Property 19: Parquet export round-trip
# Feature: matrix-watcher, Property 19: Parquet export round-trip
# Validates: Requirements 10.5
# ============================================================================

class TestParquetRoundTripProperty:
    """Property 19: Export and import back produces equivalent records."""
    
    @given(
        num_records=st.integers(min_value=1, max_value=50),
        source=simple_text
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_parquet_round_trip_preserves_records(self, num_records, source):
        """
        Feature: matrix-watcher, Property 19: Parquet export round-trip
        For any set of records, export to Parquet and import back should preserve all data.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.parquet")
            
            # Create records
            original_records = [
                {
                    "timestamp": 1700000000.0 + i,
                    "source": source,
                    "index": i,
                    "value": float(i * 10)
                }
                for i in range(num_records)
            ]
            
            # Export
            exported = export_to_parquet(iter(original_records), output_path)
            assert exported == num_records
            
            # Import
            restored_records = import_from_parquet(output_path)
            
            assert len(restored_records) == num_records
            
            for i, (orig, restored) in enumerate(zip(original_records, restored_records)):
                assert restored["timestamp"] == orig["timestamp"], f"Record {i} timestamp mismatch"
                assert restored["source"] == orig["source"], f"Record {i} source mismatch"
                assert restored["index"] == orig["index"], f"Record {i} index mismatch"
                assert restored["value"] == orig["value"], f"Record {i} value mismatch"
    
    @given(
        timestamp=timestamp_strategy,
        source=simple_text,
        int_val=st.integers(min_value=-10000, max_value=10000),
        float_val=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_single_record_round_trip(self, timestamp, source, int_val, float_val):
        """
        Feature: matrix-watcher, Property 19: Parquet export round-trip
        Single record should round-trip correctly.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "single.parquet")
            
            original = {
                "timestamp": timestamp,
                "source": source,
                "int_val": int_val,
                "float_val": float_val
            }
            
            export_to_parquet(iter([original]), output_path)
            restored = import_from_parquet(output_path)
            
            assert len(restored) == 1
            assert restored[0]["timestamp"] == original["timestamp"]
            assert restored[0]["source"] == original["source"]
            assert restored[0]["int_val"] == original["int_val"]
            assert abs(restored[0]["float_val"] - original["float_val"]) < 1e-10


class TestParquetExporterFunctionality:
    """Additional Parquet exporter functionality tests."""
    
    def test_empty_records_returns_zero(self):
        """Exporting empty records should return 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "empty.parquet")
            
            exported = export_to_parquet(iter([]), output_path)
            assert exported == 0
    
    def test_compression_options(self):
        """Test different compression options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            records = [
                {"timestamp": 1700000000.0 + i, "source": "test", "data": "x" * 100}
                for i in range(100)
            ]
            
            for compression in ["snappy", "gzip", "none"]:
                output_path = os.path.join(tmpdir, f"test_{compression}.parquet")
                exporter = ParquetExporter(compression=compression)
                
                exported = exporter.export(iter(records), output_path)
                assert exported == 100
                
                # Verify file exists and can be read
                restored = import_from_parquet(output_path)
                assert len(restored) == 100
    
    def test_read_parquet_returns_dataframe(self):
        """Test reading Parquet as DataFrame."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "df_test.parquet")
            
            records = [
                {"timestamp": 1700000000.0 + i, "source": "test", "value": i}
                for i in range(10)
            ]
            
            export_to_parquet(iter(records), output_path)
            
            df = ParquetExporter.read_parquet(output_path)
            
            assert len(df) == 10
            assert "timestamp" in df.columns
            assert "source" in df.columns
            assert "value" in df.columns
    
    def test_chunked_export(self):
        """Test export with chunking for large datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "chunked.parquet")
            
            # Create more records than chunk size
            records = [
                {"timestamp": 1700000000.0 + i, "source": "test", "index": i}
                for i in range(25000)
            ]
            
            exporter = ParquetExporter()
            exported = exporter.export(iter(records), output_path, chunk_size=10000)
            
            assert exported == 25000
            
            restored = import_from_parquet(output_path)
            assert len(restored) == 25000
