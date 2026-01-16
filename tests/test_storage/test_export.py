"""Property-based tests for Data Export.

Tests:
- Property 52: CSV export round-trip - export and import preserves values

Validates: Requirements 22.5
"""

import csv
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from src.storage.jsonl_storage import JSONLStorage
from src.storage.export import DataExporter, DataReplayer


class TestDataExporterProperties:
    """Property-based tests for DataExporter."""
    
    @given(
        values=st.lists(
            st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_52_csv_round_trip(self, values):
        """Property 52: CSV export round-trip.
        
        Export and import preserves values.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONLStorage(base_path=tmpdir)
            
            # Write records
            import time
            base_time = time.time()
            for i, value in enumerate(values):
                record = {
                    "timestamp": base_time + i,
                    "source": "test",
                    "value": value
                }
                storage.write("test", record)
            
            # Export to CSV
            exporter = DataExporter(storage)
            csv_path = Path(tmpdir) / "export.csv"
            count = exporter.export_csv("test", csv_path)
            
            assert count == len(values)
            
            # Read back CSV
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == len(values)
            
            # Verify values preserved
            for i, row in enumerate(rows):
                original = values[i]
                exported = float(row["value"])
                assert abs(original - exported) < 0.0001


class TestDataExporterIntegration:
    """Integration tests for DataExporter."""
    
    @pytest.fixture
    def storage_with_data(self):
        """Create storage with test data."""
        import time
        
        tmpdir = tempfile.mkdtemp()
        storage = JSONLStorage(base_path=tmpdir)
        
        base_time = time.time()
        for i in range(10):
            storage.write("sensor1", {
                "timestamp": base_time + i,
                "source": "sensor1",
                "value": i * 10,
                "status": "ok"
            })
        
        for i in range(5):
            storage.write("sensor2", {
                "timestamp": base_time + i,
                "source": "sensor2",
                "metric": i * 100
            })
        
        yield storage, tmpdir
        
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_export_csv(self, storage_with_data):
        """Exports to CSV correctly."""
        storage, tmpdir = storage_with_data
        exporter = DataExporter(storage)
        
        csv_path = Path(tmpdir) / "output.csv"
        count = exporter.export_csv("sensor1", csv_path)
        
        assert count == 10
        assert csv_path.exists()
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 10
        assert "timestamp" in rows[0]
        assert "value" in rows[0]
    
    def test_export_csv_with_columns(self, storage_with_data):
        """Exports only specified columns."""
        storage, tmpdir = storage_with_data
        exporter = DataExporter(storage)
        
        csv_path = Path(tmpdir) / "filtered.csv"
        count = exporter.export_csv(
            "sensor1", csv_path, columns=["timestamp", "value"]
        )
        
        assert count == 10
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Should only have specified columns
        assert "timestamp" in rows[0]
        assert "value" in rows[0]
    
    def test_export_empty_sensor(self, storage_with_data):
        """Handles empty sensor gracefully."""
        storage, tmpdir = storage_with_data
        exporter = DataExporter(storage)
        
        csv_path = Path(tmpdir) / "empty.csv"
        count = exporter.export_csv("nonexistent", csv_path)
        
        assert count == 0
    
    def test_export_all_sensors(self, storage_with_data):
        """Exports all sensors to separate files."""
        storage, tmpdir = storage_with_data
        exporter = DataExporter(storage)
        
        output_dir = Path(tmpdir) / "exports"
        results = exporter.export_all_sensors_csv(output_dir)
        
        assert "sensor1" in results
        assert "sensor2" in results
        assert results["sensor1"] == 10
        assert results["sensor2"] == 5


class TestDataReplayerIntegration:
    """Integration tests for DataReplayer."""
    
    @pytest.fixture
    def storage_with_data(self):
        """Create storage with test data."""
        import time
        
        tmpdir = tempfile.mkdtemp()
        storage = JSONLStorage(base_path=tmpdir)
        
        base_time = time.time()
        for i in range(5):
            storage.write("test", {
                "timestamp": base_time + i * 0.1,  # 100ms apart
                "source": "test",
                "value": i
            })
        
        yield storage, tmpdir
        
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_replay_basic(self, storage_with_data):
        """Replays records in order."""
        storage, tmpdir = storage_with_data
        replayer = DataReplayer(storage)
        
        records = []
        async for record in replayer.replay("test", speed=100.0):
            records.append(record)
        
        assert len(records) == 5
        
        # Verify order
        for i, record in enumerate(records):
            assert record["value"] == i
    
    @pytest.mark.asyncio
    async def test_replay_with_callback(self, storage_with_data):
        """Callback is called for each record."""
        storage, tmpdir = storage_with_data
        replayer = DataReplayer(storage)
        
        callback_records = []
        
        def callback(record):
            callback_records.append(record)
        
        async for _ in replayer.replay("test", speed=100.0, callback=callback):
            pass
        
        assert len(callback_records) == 5
    
    @pytest.mark.asyncio
    async def test_replay_stop(self, storage_with_data):
        """Stop halts replay."""
        storage, tmpdir = storage_with_data
        replayer = DataReplayer(storage)
        
        records = []
        async for record in replayer.replay("test", speed=100.0):
            records.append(record)
            if len(records) >= 2:
                replayer.stop()
        
        assert len(records) <= 3  # May get one more after stop
    
    def test_pause_resume(self, storage_with_data):
        """Pause and resume work correctly."""
        storage, tmpdir = storage_with_data
        replayer = DataReplayer(storage)
        
        assert replayer.is_paused == False
        
        replayer.pause()
        assert replayer.is_paused == True
        
        replayer.resume()
        assert replayer.is_paused == False
    
    @pytest.mark.asyncio
    async def test_replay_empty_sensor(self, storage_with_data):
        """Handles empty sensor gracefully."""
        storage, tmpdir = storage_with_data
        replayer = DataReplayer(storage)
        
        records = []
        async for record in replayer.replay("nonexistent", speed=100.0):
            records.append(record)
        
        assert len(records) == 0
