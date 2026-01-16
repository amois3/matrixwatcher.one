"""Property-based tests for core types.

Feature: matrix-watcher, Property 21: Record structure
Validates: Requirements 10.7
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from src.core.types import (
    Event, SensorReading, AnomalyEvent, EventType, SensorStatus, 
    Priority, Severity, TaskStats
)

# Simplified strategies for faster generation
simple_text = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
simple_payload = st.dictionaries(
    simple_text,
    st.one_of(st.integers(min_value=-1000, max_value=1000), st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)),
    max_size=5
)


# ============================================================================
# Property 21: Record structure - verify all records contain timestamp and source
# Feature: matrix-watcher, Property 21: Record structure
# Validates: Requirements 10.7
# ============================================================================

class TestRecordStructureProperty:
    """Property 21: All records must contain timestamp and source fields."""
    
    @given(
        timestamp=st.floats(min_value=0, max_value=2**31, allow_nan=False, allow_infinity=False),
        source=simple_text,
        event_type=st.sampled_from(list(EventType)),
        payload=simple_payload
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_event_contains_timestamp_and_source(self, timestamp, source, event_type, payload):
        """
        Feature: matrix-watcher, Property 21: Record structure
        For any Event, the serialized dict must contain 'timestamp' and 'source' fields.
        """
        event = Event(
            timestamp=timestamp,
            source=source,
            event_type=event_type,
            payload=payload
        )
        
        event_dict = event.to_dict()
        
        assert "timestamp" in event_dict, "Event must contain 'timestamp' field"
        assert "source" in event_dict, "Event must contain 'source' field"
        assert event_dict["timestamp"] == timestamp
        assert event_dict["source"] == source
    
    @given(
        timestamp=st.floats(min_value=0, max_value=2**31, allow_nan=False, allow_infinity=False),
        source=simple_text,
        data=st.dictionaries(
            simple_text,
            st.one_of(st.integers(min_value=-1000, max_value=1000), st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_sensor_reading_contains_timestamp_and_source(self, timestamp, source, data):
        """
        Feature: matrix-watcher, Property 21: Record structure
        For any SensorReading, the serialized dict must contain 'timestamp' and 'source' fields.
        """
        reading = SensorReading(
            timestamp=timestamp,
            source=source,
            data=data
        )
        
        reading_dict = reading.to_dict()
        
        assert "timestamp" in reading_dict, "SensorReading must contain 'timestamp' field"
        assert "source" in reading_dict, "SensorReading must contain 'source' field"
        assert reading_dict["timestamp"] == timestamp
        assert reading_dict["source"] == source
    
    @given(
        timestamp=st.floats(min_value=0, max_value=2**31, allow_nan=False, allow_infinity=False),
        parameter=simple_text,
        value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        mean=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        std=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
        z_score=st.floats(min_value=-20, max_value=20, allow_nan=False, allow_infinity=False),
        sensor_source=simple_text
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_anomaly_event_contains_timestamp_and_source(
        self, timestamp, parameter, value, mean, std, z_score, sensor_source
    ):
        """
        Feature: matrix-watcher, Property 21: Record structure
        For any AnomalyEvent, the serialized dict must contain 'timestamp' and 'source' fields.
        """
        anomaly = AnomalyEvent(
            timestamp=timestamp,
            parameter=parameter,
            value=value,
            mean=mean,
            std=std,
            z_score=z_score,
            sensor_source=sensor_source
        )
        
        anomaly_dict = anomaly.to_dict()
        
        assert "timestamp" in anomaly_dict, "AnomalyEvent must contain 'timestamp' field"
        assert "source" in anomaly_dict, "AnomalyEvent must contain 'source' field"
        assert anomaly_dict["timestamp"] == timestamp
        # AnomalyEvent source is always "anomaly_detector"
        assert anomaly_dict["source"] == "anomaly_detector"


class TestEventRoundTrip:
    """Test Event serialization round-trip."""
    
    @given(
        timestamp=st.floats(min_value=0, max_value=2**31, allow_nan=False, allow_infinity=False),
        source=simple_text,
        event_type=st.sampled_from(list(EventType)),
        severity=st.sampled_from(list(Severity)),
        payload=simple_payload
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_event_round_trip(self, timestamp, source, event_type, severity, payload):
        """Event serialization and deserialization should preserve all data."""
        original = Event(
            timestamp=timestamp,
            source=source,
            event_type=event_type,
            payload=payload,
            severity=severity
        )
        
        # Round trip
        event_dict = original.to_dict()
        restored = Event.from_dict(event_dict)
        
        assert restored.timestamp == original.timestamp
        assert restored.source == original.source
        assert restored.event_type == original.event_type
        assert restored.severity == original.severity
        assert restored.payload == original.payload


class TestSensorReadingRoundTrip:
    """Test SensorReading serialization round-trip."""
    
    @given(
        timestamp=st.floats(min_value=0, max_value=2**31, allow_nan=False, allow_infinity=False),
        source=simple_text,
        data=st.dictionaries(
            simple_text,
            st.one_of(st.integers(min_value=-1000, max_value=1000), st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_sensor_reading_to_event_preserves_data(self, timestamp, source, data):
        """Converting SensorReading to Event should preserve timestamp and source."""
        reading = SensorReading(
            timestamp=timestamp,
            source=source,
            data=data
        )
        
        event = reading.to_event()
        
        assert event.timestamp == reading.timestamp
        assert event.source == reading.source
        assert event.payload == reading.data
        assert event.event_type == EventType.DATA


class TestEnumValues:
    """Test enum value consistency."""
    
    def test_event_type_values(self):
        """EventType enum should have expected values."""
        assert EventType.DATA.value == "data"
        assert EventType.ANOMALY.value == "anomaly"
        assert EventType.ERROR.value == "error"
        assert EventType.HEALTH.value == "health"
        assert EventType.ALERT.value == "alert"
    
    def test_sensor_status_values(self):
        """SensorStatus enum should have expected values."""
        assert SensorStatus.RUNNING.value == "running"
        assert SensorStatus.STOPPED.value == "stopped"
        assert SensorStatus.ERROR.value == "error"
        assert SensorStatus.RATE_LIMITED.value == "rate_limited"
        assert SensorStatus.DISABLED.value == "disabled"
    
    def test_priority_values(self):
        """Priority enum should have expected values."""
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"
    
    def test_severity_values(self):
        """Severity enum should have expected values."""
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.CRITICAL.value == "critical"
