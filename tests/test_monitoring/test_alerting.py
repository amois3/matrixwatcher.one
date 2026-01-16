"""Property-based tests for Alerting System.

Tests:
- Property 51: Cooldown enforcement - duplicate alerts suppressed during cooldown

Validates: Requirements 21.4
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.monitoring.alerting import (
    AlertingSystem, Alert, AlertType, AlertPriority
)


class TestAlertingSystemProperties:
    """Property-based tests for AlertingSystem."""
    
    @given(
        cooldown=st.floats(min_value=1.0, max_value=600.0)
    )
    @settings(max_examples=100)
    def test_property_51_cooldown_enforcement(self, cooldown):
        """Property 51: Cooldown enforcement.
        
        Duplicate alerts are suppressed during cooldown period.
        """
        alerting = AlertingSystem(cooldown_seconds=cooldown)
        
        alert = Alert(
            alert_type=AlertType.SENSOR_FAILURE,
            priority=AlertPriority.HIGH,
            title="Test Alert",
            message="Test message"
        )
        
        # First alert should pass
        assert alerting._should_send(alert) == True
        
        # Simulate sending (update last_alerts)
        alerting._last_alerts[alert.alert_id] = time.time()
        
        # Second alert should be suppressed
        assert alerting._should_send(alert) == False
    
    @given(
        min_priority=st.sampled_from(list(AlertPriority))
    )
    @settings(max_examples=100)
    def test_priority_filtering(self, min_priority):
        """Alerts below minimum priority are filtered."""
        alerting = AlertingSystem(min_priority=min_priority)
        
        priority_order = [AlertPriority.LOW, AlertPriority.MEDIUM, AlertPriority.HIGH, AlertPriority.CRITICAL]
        min_idx = priority_order.index(min_priority)
        
        for i, priority in enumerate(priority_order):
            alert = Alert(
                alert_type=AlertType.ANOMALY_DETECTED,
                priority=priority,
                title="Test",
                message="Test"
            )
            
            should_send = alerting._should_send(alert)
            
            if i >= min_idx:
                assert should_send == True
            else:
                assert should_send == False


class TestAlertingSystemIntegration:
    """Integration tests for AlertingSystem."""
    
    @pytest.fixture
    def alerting(self):
        return AlertingSystem(cooldown_seconds=60.0)
    
    def test_add_webhook(self, alerting):
        """Adds webhook correctly."""
        alerting.add_webhook("https://example.com/webhook", "discord")
        
        assert len(alerting._webhooks) == 1
        assert alerting._webhooks[0].platform == "discord"
    
    def test_remove_webhook(self, alerting):
        """Removes webhook correctly."""
        alerting.add_webhook("https://example.com/webhook", "discord")
        alerting.remove_webhook("https://example.com/webhook")
        
        assert len(alerting._webhooks) == 0
    
    def test_alert_id_generation(self, alerting):
        """Alert IDs are consistent."""
        alert1 = Alert(
            alert_type=AlertType.SENSOR_FAILURE,
            priority=AlertPriority.HIGH,
            title="Test Alert",
            message="Message 1"
        )
        
        alert2 = Alert(
            alert_type=AlertType.SENSOR_FAILURE,
            priority=AlertPriority.HIGH,
            title="Test Alert",
            message="Message 2"  # Different message
        )
        
        # Same type and title = same ID
        assert alert1.alert_id == alert2.alert_id
    
    def test_different_alerts_different_ids(self, alerting):
        """Different alerts have different IDs."""
        alert1 = Alert(
            alert_type=AlertType.SENSOR_FAILURE,
            priority=AlertPriority.HIGH,
            title="Alert 1",
            message="Message"
        )
        
        alert2 = Alert(
            alert_type=AlertType.SENSOR_FAILURE,
            priority=AlertPriority.HIGH,
            title="Alert 2",
            message="Message"
        )
        
        assert alert1.alert_id != alert2.alert_id
    
    def test_format_discord_payload(self, alerting):
        """Formats Discord payload correctly."""
        alert = Alert(
            alert_type=AlertType.SENSOR_FAILURE,
            priority=AlertPriority.HIGH,
            title="Test",
            message="Test message"
        )
        
        payload = alerting._format_payload(alert, "discord")
        
        assert "embeds" in payload
        assert payload["embeds"][0]["title"].endswith("Test")
        assert payload["embeds"][0]["description"] == "Test message"
    
    def test_format_slack_payload(self, alerting):
        """Formats Slack payload correctly."""
        alert = Alert(
            alert_type=AlertType.ANOMALY_DETECTED,
            priority=AlertPriority.MEDIUM,
            title="Anomaly",
            message="Detected anomaly"
        )
        
        payload = alerting._format_payload(alert, "slack")
        
        assert "blocks" in payload
    
    def test_format_telegram_payload(self, alerting):
        """Formats Telegram payload correctly."""
        alert = Alert(
            alert_type=AlertType.RATE_LIMIT,
            priority=AlertPriority.LOW,
            title="Rate Limited",
            message="API rate limited"
        )
        
        payload = alerting._format_payload(alert, "telegram")
        
        assert "text" in payload
        assert "parse_mode" in payload
    
    def test_get_stats(self, alerting):
        """Returns statistics correctly."""
        alerting.add_webhook("https://example.com", "discord")
        
        stats = alerting.get_stats()
        
        assert stats["webhooks_configured"] == 1
        assert stats["webhooks_enabled"] == 1
        assert stats["alerts_sent"] == 0
        assert stats["alerts_suppressed"] == 0
    
    def test_cleanup_old_alerts(self, alerting):
        """Cleans up old alert entries."""
        # Add old entry
        old_time = time.time() - alerting.cooldown_seconds * 3
        alerting._last_alerts["old_alert"] = old_time
        
        # Add recent entry
        alerting._last_alerts["recent_alert"] = time.time()
        
        alerting._cleanup_old_alerts()
        
        assert "old_alert" not in alerting._last_alerts
        assert "recent_alert" in alerting._last_alerts
    
    @pytest.mark.asyncio
    async def test_send_alert_no_webhooks(self, alerting):
        """Returns False when no webhooks configured."""
        alert = Alert(
            alert_type=AlertType.SENSOR_FAILURE,
            priority=AlertPriority.HIGH,
            title="Test",
            message="Test"
        )
        
        result = await alerting.send_alert(alert)
        assert result == False
    
    def test_alert_timestamp(self):
        """Alert timestamp is set automatically."""
        before = time.time()
        alert = Alert(
            alert_type=AlertType.SYSTEM_ERROR,
            priority=AlertPriority.CRITICAL,
            title="Error",
            message="System error"
        )
        after = time.time()
        
        assert before <= alert.timestamp <= after
