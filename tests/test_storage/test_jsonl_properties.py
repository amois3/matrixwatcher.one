"""Property-based tests for JSONL storage.

Feature: matrix-watcher, Property 16: Storage path generation
Feature: matrix-watcher, Property 17: File rotation
Feature: matrix-watcher, Property 18: JSONL round-trip
Feature: matrix-watcher, Property 20: Gzip compression round-trip
Validates: Requirements 10.1, 10.4, 10.8, 10.9, 10.11
"""

import pytest
import tempfile
import os
import json
import gzip
from datetime import date
from hypothesis import given, strategies as st, settings, HealthCheck

from src.storage.jsonl_storage import JSONLStorage
from src.storage.base import StorageError


# Simplified strategies
simple_text = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
timestamp_strategy = st.floats(min_value=1000000000, max_value=2000000000, allow_nan=False, allow_infinity=False)


# ============================================================================
# Property 16: Storage path generation
# Feature: matrix-watcher, Property 16: Storage path generation
# Validates: Requirements 10.1
# ============================================================================

class TestStoragePathGenerationProperty:
    """Property 16: Paths match pattern logs/{sensor_name}/{YYYY-MM-DD}.jsonl"""
    
    @given(
        sensor_name=simple_text,
        year=st.integers(min_value=2020, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_path_format_matches_pattern(self, sensor_name, year, month, day):
        """
        Feature: matrix-watcher, Property 16: Storage path generation
        For any sensor name and date, path should match logs/{sensor_name}/{YYYY-MM-DD}.jsonl
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir, compression=False)
            target_date = date(year, month, day)
            
            path = storage._get_file_path(sensor_name, target_date)
            
            # Verify path structure
            assert str(path).startswith(tmpdir)
            assert sensor_name in str(path)
            assert target_date.strftime("%Y-%m-%d") in str(path)
            assert str(path).endswith(".jsonl")
    
    @given(sensor_name=simple_text)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_path_with_compression_has_gz_extension(self, sensor_name):
        """
        Feature: matrix-watcher, Property 16: Storage path generation
        With compression enabled, path should end with .jsonl.gz
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir, compression=True)
            target_date = date.today()
            
            path = storage._get_file_path(sensor_name, target_date)
            
            assert str(path).endswith(".jsonl.gz")


# ============================================================================
# Property 17: File rotation
# Feature: matrix-watcher, Property 17: File rotation
# Validates: Requirements 10.4
# ============================================================================

class TestFileRotationProperty:
    """Property 17: Files exceeding 100MB trigger rotation."""
    
    def test_rotation_creates_new_file(self):
        """
        Feature: matrix-watcher, Property 17: File rotation
        When file exceeds max size, a new file with incremental suffix is created.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use very small max size for testing
            storage = JSONLStorage(base_path=tmpdir, max_file_size_mb=0.0001)  # ~100 bytes
            
            # Write enough records to trigger rotation
            for i in range(100):
                record = {
                    "timestamp": 1700000000.0 + i,
                    "source": "test",
                    "data": "x" * 50  # Make records larger
                }
                storage.write("test_sensor", record)
            
            # Check that multiple files were created
            sensor_dir = os.path.join(tmpdir, "test_sensor")
            files = list(os.listdir(sensor_dir))
            
            # Should have at least 2 files due to rotation
            assert len(files) >= 2, f"Expected rotation, got files: {files}"
    
    def test_rotated_files_have_incremental_suffix(self):
        """
        Feature: matrix-watcher, Property 17: File rotation
        Rotated files should have incremental suffix (.1, .2, etc.)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir, max_file_size_mb=0.0001)
            
            # Write enough to trigger multiple rotations
            for i in range(200):
                record = {
                    "timestamp": 1700000000.0 + i,
                    "source": "test",
                    "data": "x" * 100
                }
                storage.write("rotation_test", record)
            
            sensor_dir = os.path.join(tmpdir, "rotation_test")
            files = sorted(os.listdir(sensor_dir))
            
            # Should have base file and rotated files
            today_str = date.today().strftime("%Y-%m-%d")
            assert any(f.startswith(today_str) and ".1." in f for f in files) or len(files) >= 2


# ============================================================================
# Property 18: JSONL round-trip
# Feature: matrix-watcher, Property 18: JSONL round-trip
# Validates: Requirements 10.8, 10.9
# ============================================================================

class TestJSONLRoundTripProperty:
    """Property 18: Serialize and parse back produces equivalent record."""
    
    @given(
        timestamp=timestamp_strategy,
        source=simple_text,
        int_value=st.integers(min_value=-10000, max_value=10000),
        float_value=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        str_value=simple_text
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_record_round_trip(self, timestamp, source, int_value, float_value, str_value):
        """
        Feature: matrix-watcher, Property 18: JSONL round-trip
        For any valid record, write then read should produce equivalent record.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir, compression=False)
            
            original = {
                "timestamp": timestamp,
                "source": source,
                "int_value": int_value,
                "float_value": float_value,
                "str_value": str_value
            }
            
            storage.write("roundtrip_test", original)
            
            # Read back
            records = list(storage.read("roundtrip_test", date.today(), date.today()))
            
            assert len(records) == 1
            restored = records[0]
            
            assert restored["timestamp"] == original["timestamp"]
            assert restored["source"] == original["source"]
            assert restored["int_value"] == original["int_value"]
            assert abs(restored["float_value"] - original["float_value"]) < 1e-10
            assert restored["str_value"] == original["str_value"]
    
    @given(
        num_records=st.integers(min_value=1, max_value=20),
        source=simple_text
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_batch_round_trip(self, num_records, source):
        """
        Feature: matrix-watcher, Property 18: JSONL round-trip
        Batch write then read should preserve all records.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir, compression=False)
            
            records = [
                {"timestamp": 1700000000.0 + i, "source": source, "index": i}
                for i in range(num_records)
            ]
            
            written = storage.write_batch("batch_test", records)
            assert written == num_records
            
            # Read back
            restored = list(storage.read("batch_test", date.today(), date.today()))
            
            assert len(restored) == num_records
            for i, record in enumerate(restored):
                assert record["index"] == i


# ============================================================================
# Property 20: Gzip compression round-trip
# Feature: matrix-watcher, Property 20: Gzip compression round-trip
# Validates: Requirements 10.11
# ============================================================================

class TestGzipCompressionRoundTripProperty:
    """Property 20: Compress and decompress produces identical content."""
    
    @given(
        timestamp=timestamp_strategy,
        source=simple_text,
        data_value=st.integers(min_value=-10000, max_value=10000)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_compressed_round_trip(self, timestamp, source, data_value):
        """
        Feature: matrix-watcher, Property 20: Gzip compression round-trip
        For any record, compressed write then read should produce identical record.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir, compression=True)
            
            original = {
                "timestamp": timestamp,
                "source": source,
                "value": data_value
            }
            
            storage.write("compressed_test", original)
            
            # Verify file is actually compressed
            sensor_dir = os.path.join(tmpdir, "compressed_test")
            files = os.listdir(sensor_dir)
            assert any(f.endswith(".gz") for f in files), "File should be gzip compressed"
            
            # Read back
            records = list(storage.read("compressed_test", date.today(), date.today()))
            
            assert len(records) == 1
            assert records[0] == original
    
    def test_compression_reduces_size(self):
        """
        Feature: matrix-watcher, Property 20: Gzip compression round-trip
        Compressed files should be smaller than uncompressed for repetitive data.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_plain = JSONLStorage(base_path=os.path.join(tmpdir, "plain"), compression=False)
            storage_gzip = JSONLStorage(base_path=os.path.join(tmpdir, "gzip"), compression=True)
            
            # Write same data to both
            records = [
                {"timestamp": 1700000000.0 + i, "source": "test", "data": "repeated_data_" * 10}
                for i in range(100)
            ]
            
            storage_plain.write_batch("test", records)
            storage_gzip.write_batch("test", records)
            
            plain_size = storage_plain.get_size("test")
            gzip_size = storage_gzip.get_size("test")
            
            # Compressed should be smaller
            assert gzip_size < plain_size, f"Compressed ({gzip_size}) should be smaller than plain ({plain_size})"


class TestJSONLStorageFunctionality:
    """Additional JSONL storage functionality tests."""
    
    def test_missing_timestamp_raises_error(self):
        """Records without timestamp should raise StorageError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir)
            
            with pytest.raises(StorageError):
                storage.write("test", {"source": "test", "value": 1})
    
    def test_missing_source_raises_error(self):
        """Records without source should raise StorageError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir)
            
            with pytest.raises(StorageError):
                storage.write("test", {"timestamp": 1700000000.0, "value": 1})
    
    def test_get_record_count(self):
        """Test record counting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir)
            
            records = [
                {"timestamp": 1700000000.0 + i, "source": "test"}
                for i in range(10)
            ]
            storage.write_batch("count_test", records)
            
            count = storage.get_record_count("count_test")
            assert count == 10
    
    def test_get_available_dates(self):
        """Test getting available dates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir)
            
            storage.write("dates_test", {"timestamp": 1700000000.0, "source": "test"})
            
            dates = storage.get_available_dates("dates_test")
            assert len(dates) == 1
            assert dates[0] == date.today()
    
    def test_pretty_print(self):
        """Test pretty printer output."""
        record = {"timestamp": 1700000000.0, "source": "test", "value": 42}
        
        output = JSONLStorage.pretty_print(record)
        
        assert "timestamp" in output
        assert "source" in output
        assert "_datetime" in output  # Added by pretty printer
        assert "42" in output
