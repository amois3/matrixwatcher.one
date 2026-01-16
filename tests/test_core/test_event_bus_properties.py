"""Property-based tests for Event Bus.

Feature: matrix-watcher, Property 44: Event delivery
Feature: matrix-watcher, Property 45: Buffer overflow handling
Feature: matrix-watcher, Property 46: Event filtering
Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import time

from src.core.event_bus import EventBus, EventFilter, Subscription
from src.core.types import Event, EventType, Severity


# Simplified strategies
simple_text = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
simple_payload = st.dictionaries(
    simple_text,
    st.integers(min_value=-1000, max_value=1000),
    max_size=3
)


# ============================================================================
# Property 44: Event delivery
# Feature: matrix-watcher, Property 44: Event delivery
# Validates: Requirements 17.1, 17.2
# ============================================================================

class TestEventDeliveryProperty:
    """Property 44: All subscribers receive published events."""
    
    @given(
        num_subscribers=st.integers(min_value=1, max_value=10),
        num_events=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_all_subscribers_receive_events(self, num_subscribers, num_events):
        """
        Feature: matrix-watcher, Property 44: Event delivery
        For any number of subscribers, all should receive all published events.
        """
        bus = EventBus()
        received: dict[str, list[Event]] = {}
        
        # Create subscribers
        sub_ids = []
        for i in range(num_subscribers):
            received[f"sub_{i}"] = []
            
            def make_handler(key):
                def handler(event):
                    received[key].append(event)
                return handler
            
            sub_id = bus.subscribe(make_handler(f"sub_{i}"))
            sub_ids.append(sub_id)
        
        # Publish events
        events = []
        for i in range(num_events):
            event = Event.create(
                source=f"test_{i}",
                event_type=EventType.DATA,
                payload={"index": i}
            )
            events.append(event)
            bus.publish(event)
        
        # Verify all subscribers received all events
        for key in received:
            assert len(received[key]) == num_events, \
                f"Subscriber {key} received {len(received[key])} events, expected {num_events}"
        
        # Cleanup
        for sub_id in sub_ids:
            bus.unsubscribe(sub_id)
    
    @given(
        source=simple_text,
        event_type=st.sampled_from(list(EventType)),
        payload=simple_payload
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_event_delivered_unchanged(self, source, event_type, payload):
        """
        Feature: matrix-watcher, Property 44: Event delivery
        Events should be delivered unchanged to subscribers.
        """
        bus = EventBus()
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        bus.subscribe(handler)
        
        original = Event.create(source=source, event_type=event_type, payload=payload)
        bus.publish(original)
        
        assert len(received_events) == 1
        received = received_events[0]
        assert received.source == original.source
        assert received.event_type == original.event_type
        assert received.payload == original.payload


# ============================================================================
# Property 45: Buffer overflow handling
# Feature: matrix-watcher, Property 45: Buffer overflow handling
# Validates: Requirements 17.3, 17.4
# ============================================================================

class TestBufferOverflowProperty:
    """Property 45: Oldest events dropped first when buffer exceeds 1000."""
    
    def test_buffer_drops_oldest_on_overflow(self):
        """
        Feature: matrix-watcher, Property 45: Buffer overflow handling
        When buffer exceeds max size, oldest events should be dropped first.
        """
        max_buffer = 10  # Small buffer for testing
        bus = EventBus(max_buffer_size=max_buffer)
        
        # Create a subscriber that always fails (to trigger buffering)
        fail_count = [0]
        
        def failing_handler(event):
            fail_count[0] += 1
            raise Exception("Simulated failure")
        
        sub_id = bus.subscribe(failing_handler)
        
        # Publish more events than buffer can hold
        num_events = max_buffer + 5
        for i in range(num_events):
            event = Event.create(
                source="test",
                event_type=EventType.DATA,
                payload={"index": i}
            )
            bus.publish(event)
        
        # Check that dropped count is correct
        dropped = bus.get_dropped_count(sub_id)
        assert dropped == num_events - max_buffer, \
            f"Expected {num_events - max_buffer} dropped, got {dropped}"
        
        # Buffer should be at max size
        buffer_size = bus.get_buffer_size(sub_id)
        assert buffer_size == max_buffer
    
    @given(
        buffer_size=st.integers(min_value=5, max_value=50),
        overflow_amount=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_buffer_size_never_exceeds_max(self, buffer_size, overflow_amount):
        """
        Feature: matrix-watcher, Property 45: Buffer overflow handling
        Buffer size should never exceed configured maximum.
        """
        bus = EventBus(max_buffer_size=buffer_size)
        
        def failing_handler(event):
            raise Exception("Simulated failure")
        
        sub_id = bus.subscribe(failing_handler)
        
        # Publish more events than buffer can hold
        total_events = buffer_size + overflow_amount
        for i in range(total_events):
            event = Event.create(
                source="test",
                event_type=EventType.DATA,
                payload={"index": i}
            )
            bus.publish(event)
        
        # Buffer should not exceed max
        actual_buffer = bus.get_buffer_size(sub_id)
        assert actual_buffer <= buffer_size


# ============================================================================
# Property 46: Event filtering
# Feature: matrix-watcher, Property 46: Event filtering
# Validates: Requirements 17.5
# ============================================================================

class TestEventFilteringProperty:
    """Property 46: Only matching events delivered to filtered subscribers."""
    
    @given(
        target_type=st.sampled_from(list(EventType)),
        other_types=st.lists(st.sampled_from(list(EventType)), min_size=1, max_size=3)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_filter_by_event_type(self, target_type, other_types):
        """
        Feature: matrix-watcher, Property 46: Event filtering
        Subscriber with type filter should only receive matching events.
        """
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        # Subscribe with filter for specific type
        bus.subscribe(handler, event_types=[target_type])
        
        # Publish events of different types
        all_types = [target_type] + other_types
        for event_type in all_types:
            event = Event.create(
                source="test",
                event_type=event_type,
                payload={}
            )
            bus.publish(event)
        
        # Should only receive events of target type
        target_count = sum(1 for t in all_types if t == target_type)
        assert len(received) == target_count
        for event in received:
            assert event.event_type == target_type
    
    @given(
        target_source=simple_text,
        other_sources=st.lists(simple_text, min_size=1, max_size=3)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_filter_by_source(self, target_source, other_sources):
        """
        Feature: matrix-watcher, Property 46: Event filtering
        Subscriber with source filter should only receive matching events.
        """
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        # Subscribe with filter for specific source
        bus.subscribe(handler, sources=[target_source])
        
        # Publish events from different sources
        all_sources = [target_source] + other_sources
        for source in all_sources:
            event = Event.create(
                source=source,
                event_type=EventType.DATA,
                payload={}
            )
            bus.publish(event)
        
        # Should only receive events from target source
        target_count = sum(1 for s in all_sources if s == target_source)
        assert len(received) == target_count
        for event in received:
            assert event.source == target_source
    
    def test_filter_by_severity(self):
        """
        Feature: matrix-watcher, Property 46: Event filtering
        Subscriber with severity filter should only receive events at or above threshold.
        """
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        # Subscribe with minimum severity WARNING
        bus.subscribe(handler, min_severity=Severity.WARNING)
        
        # Publish events of different severities
        for severity in [Severity.INFO, Severity.WARNING, Severity.CRITICAL]:
            event = Event(
                timestamp=time.time(),
                source="test",
                event_type=EventType.DATA,
                payload={},
                severity=severity
            )
            bus.publish(event)
        
        # Should only receive WARNING and CRITICAL
        assert len(received) == 2
        severities = {e.severity for e in received}
        assert Severity.INFO not in severities
        assert Severity.WARNING in severities
        assert Severity.CRITICAL in severities


class TestEventBusFunctionality:
    """Additional Event Bus functionality tests."""
    
    def test_unsubscribe_stops_delivery(self):
        """Unsubscribed handlers should not receive events."""
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        sub_id = bus.subscribe(handler)
        
        # Publish first event
        bus.publish(Event.create("test", EventType.DATA, {}))
        assert len(received) == 1
        
        # Unsubscribe
        result = bus.unsubscribe(sub_id)
        assert result is True
        
        # Publish second event
        bus.publish(Event.create("test", EventType.DATA, {}))
        assert len(received) == 1  # Should not increase
    
    def test_stats_tracking(self):
        """Event bus should track statistics."""
        bus = EventBus()
        
        def handler(event):
            pass
        
        bus.subscribe(handler)
        bus.subscribe(handler)
        
        for _ in range(5):
            bus.publish(Event.create("test", EventType.DATA, {}))
        
        stats = bus.get_stats()
        assert stats["subscriber_count"] == 2
        assert stats["total_published"] == 5
        assert stats["total_delivered"] == 10  # 5 events * 2 subscribers
    
    def test_clear_removes_all_subscriptions(self):
        """Clear should remove all subscriptions."""
        bus = EventBus()
        
        for _ in range(5):
            bus.subscribe(lambda e: None)
        
        assert bus.get_stats()["subscriber_count"] == 5
        
        bus.clear()
        
        assert bus.get_stats()["subscriber_count"] == 0
