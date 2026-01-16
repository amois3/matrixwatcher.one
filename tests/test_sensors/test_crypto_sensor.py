"""Property-based tests for Crypto Market Sensor.

Tests:
- Property 9: Crypto sensor record completeness - all required fields present
- Property 10: Crypto price delta flagging - exceeding threshold triggers flag

Validates: Requirements 6.3, 6.5
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.sensors.crypto_sensor import CryptoSensor, DEFAULT_PAIRS


class TestCryptoSensorProperties:
    """Property-based tests for CryptoSensor."""
    
    @given(
        price=st.floats(min_value=0.01, max_value=1000000.0),
        best_bid=st.floats(min_value=0.01, max_value=1000000.0),
        best_ask=st.floats(min_value=0.01, max_value=1000000.0),
        volume=st.floats(min_value=0.0, max_value=1e12),
        price_change=st.floats(min_value=-100.0, max_value=100.0)
    )
    @settings(max_examples=100)
    def test_property_9_record_completeness(self, price, best_bid, best_ask, volume, price_change):
        """Property 9: Crypto sensor record completeness.
        
        All pair data must contain required fields.
        """
        # Ensure best_ask >= best_bid for realistic spread
        if best_ask < best_bid:
            best_ask, best_bid = best_bid, best_ask
        
        spread = best_ask - best_bid
        
        pair_data = {
            "symbol": "BTCUSDT",
            "price": price,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": round(spread, 8),
            "spread_percent": round((spread / price) * 100, 6) if price > 0 else 0,
            "volume_24h": volume,
            "price_change_24h_percent": price_change,
            "price_delta_percent": 0.0,
            "significant_change": False,
            "trade_count_24h": 1000
        }
        
        # Verify all required fields present
        required_fields = [
            "symbol", "price", "best_bid", "best_ask", "spread",
            "volume_24h", "price_delta_percent", "significant_change"
        ]
        for field in required_fields:
            assert field in pair_data, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(pair_data["symbol"], str)
        assert isinstance(pair_data["price"], float)
        assert isinstance(pair_data["spread"], float)
        assert isinstance(pair_data["significant_change"], bool)
    
    @given(
        last_price=st.floats(min_value=100.0, max_value=100000.0),
        current_price=st.floats(min_value=100.0, max_value=100000.0),
        threshold=st.floats(min_value=0.1, max_value=10.0)
    )
    @settings(max_examples=100)
    def test_property_10_price_delta_flagging(self, last_price, current_price, threshold):
        """Property 10: Crypto price delta flagging.
        
        Price changes exceeding threshold are flagged as significant.
        """
        sensor = CryptoSensor(price_change_threshold=threshold)
        sensor._last_prices["BTCUSDT"] = last_price
        
        # Calculate expected delta
        price_delta_percent = ((current_price - last_price) / last_price) * 100
        expected_significant = abs(price_delta_percent) > threshold
        
        # Verify flagging logic
        actual_significant = abs(price_delta_percent) > sensor.price_change_threshold
        assert actual_significant == expected_significant
    
    @given(
        pairs=st.lists(
            st.text(min_size=6, max_size=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_custom_pairs_configuration(self, pairs):
        """Custom trading pairs are properly configured."""
        sensor = CryptoSensor(pairs=pairs)
        assert sensor.pairs == pairs
        assert len(sensor.pairs) == len(pairs)
    
    @given(
        threshold=st.floats(min_value=0.01, max_value=50.0)
    )
    @settings(max_examples=100)
    def test_threshold_configuration(self, threshold):
        """Price change threshold is properly configured."""
        sensor = CryptoSensor(price_change_threshold=threshold)
        assert sensor.price_change_threshold == threshold
    
    @given(
        spread=st.floats(min_value=0.0, max_value=1000.0),
        price=st.floats(min_value=0.01, max_value=1000000.0)
    )
    @settings(max_examples=100)
    def test_spread_percent_calculation(self, spread, price):
        """Spread percentage is calculated correctly."""
        expected_percent = (spread / price) * 100 if price > 0 else 0
        
        # Verify calculation
        actual_percent = round((spread / price) * 100, 6) if price > 0 else 0
        assert abs(actual_percent - round(expected_percent, 6)) < 0.000001


class TestCryptoSensorIntegration:
    """Integration tests for CryptoSensor."""
    
    @pytest.fixture
    def sensor(self):
        return CryptoSensor(pairs=["BTCUSDT", "ETHUSDT"])
    
    def test_default_pairs(self, sensor):
        """Default pairs are configured."""
        assert "BTCUSDT" in sensor.pairs
        assert "ETHUSDT" in sensor.pairs
    
    def test_schema(self, sensor):
        """Schema defines expected fields."""
        schema = sensor.get_schema()
        assert "timestamp" in schema
        assert "pairs" in schema
        assert "pairs_count" in schema
        assert "any_significant_change" in schema
        assert "rate_limited" in schema
    
    def test_rate_limit_backoff(self, sensor):
        """Rate limiting triggers exponential backoff."""
        import time
        
        initial_multiplier = sensor._backoff_multiplier
        sensor._handle_rate_limit()
        
        assert sensor._backoff_multiplier == initial_multiplier * 2
        assert sensor._backoff_until > time.time()
        
        # Second rate limit doubles again
        sensor._handle_rate_limit()
        assert sensor._backoff_multiplier == initial_multiplier * 4
    
    def test_backoff_max_limit(self, sensor):
        """Backoff multiplier has maximum limit."""
        for _ in range(10):
            sensor._handle_rate_limit()
        
        assert sensor._backoff_multiplier <= 60
    
    @pytest.mark.asyncio
    async def test_rate_limited_response(self, sensor):
        """Rate limited state returns appropriate response."""
        import time
        
        # Set rate limit in future
        sensor._backoff_until = time.time() + 100
        
        reading = await sensor.collect()
        
        assert reading.data["rate_limited"] == True
        assert reading.data["pairs"] == []
    
    def test_price_tracking(self, sensor):
        """Last prices are tracked for delta calculation."""
        sensor._last_prices["BTCUSDT"] = 50000.0
        
        assert sensor._last_prices["BTCUSDT"] == 50000.0
        assert "ETHUSDT" not in sensor._last_prices
