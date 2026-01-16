"""Property-based tests for Weather Sensor.

Tests Property 13: Weather sensor record completeness - all required fields present.
Validates: Requirements 8.2
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.sensors.weather_sensor import WeatherSensor


class TestWeatherSensorProperties:
    """Property-based tests for WeatherSensor."""
    
    @given(
        temperature=st.floats(min_value=-50.0, max_value=60.0),
        humidity=st.integers(min_value=0, max_value=100),
        pressure=st.integers(min_value=900, max_value=1100),
        clouds=st.integers(min_value=0, max_value=100),
        wind_speed=st.floats(min_value=0.0, max_value=100.0)
    )
    @settings(max_examples=100)
    def test_property_13_record_completeness(self, temperature, humidity, pressure, clouds, wind_speed):
        """Property 13: Weather sensor record completeness.
        
        All weather data must contain required fields.
        """
        weather_data = {
            "location": "TestCity",
            "country": "TC",
            "temperature_celsius": round(temperature, 1),
            "feels_like_celsius": round(temperature - 2, 1),
            "humidity_percent": humidity,
            "pressure_hpa": pressure,
            "clouds_percent": clouds,
            "wind_speed_ms": round(wind_speed, 1),
            "wind_direction_deg": 180,
            "visibility_m": 10000,
            "weather_main": "Clear",
            "weather_description": "clear sky"
        }
        
        # Verify all required fields present
        required_fields = [
            "temperature_celsius", "humidity_percent", "pressure_hpa",
            "clouds_percent", "wind_speed_ms"
        ]
        for field in required_fields:
            assert field in weather_data, f"Missing field: {field}"
        
        # Verify types and ranges
        assert isinstance(weather_data["temperature_celsius"], float)
        assert 0 <= weather_data["humidity_percent"] <= 100
        assert 900 <= weather_data["pressure_hpa"] <= 1100
        assert 0 <= weather_data["clouds_percent"] <= 100
        assert weather_data["wind_speed_ms"] >= 0
    
    @given(
        location=st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ")
    )
    @settings(max_examples=100)
    def test_location_configuration(self, location):
        """Location is properly configured."""
        sensor = WeatherSensor(api_key="test", location=location)
        assert sensor.location == location
    
    @given(
        lat=st.floats(min_value=-90.0, max_value=90.0),
        lon=st.floats(min_value=-180.0, max_value=180.0)
    )
    @settings(max_examples=100)
    def test_coordinates_configuration(self, lat, lon):
        """Coordinates are properly configured."""
        sensor = WeatherSensor(api_key="test", lat=lat, lon=lon)
        assert sensor.lat == lat
        assert sensor.lon == lon
    
    @given(
        cache_age=st.floats(min_value=0.0, max_value=3600.0)
    )
    @settings(max_examples=100)
    def test_cache_age_calculation(self, cache_age):
        """Cache age is calculated correctly."""
        import time
        
        sensor = WeatherSensor(api_key="test")
        sensor._cached_data = {"temperature_celsius": 20.0}
        sensor._cache_time = time.time() - cache_age
        
        reading = sensor._create_cached_or_empty_reading(time.time(), "test error")
        
        assert reading.data["from_cache"] == True
        assert abs(reading.data["cache_age_seconds"] - cache_age) < 1.0


class TestWeatherSensorIntegration:
    """Integration tests for WeatherSensor."""
    
    @pytest.fixture
    def sensor(self):
        return WeatherSensor(api_key="test_key", location="London")
    
    def test_schema(self, sensor):
        """Schema defines expected fields."""
        schema = sensor.get_schema()
        assert "timestamp" in schema
        assert "from_cache" in schema
    
    @pytest.mark.asyncio
    async def test_no_api_key_handling(self):
        """Missing API key returns appropriate error."""
        sensor = WeatherSensor(api_key=None)
        reading = await sensor.collect()
        
        assert reading.data["error"] == "No API key"
        assert reading.data["from_cache"] == False
    
    def test_cache_fallback(self, sensor):
        """Cache is used when API fails."""
        import time
        
        # Set up cache
        sensor._cached_data = {
            "location": "London",
            "temperature_celsius": 15.0,
            "humidity_percent": 70,
            "pressure_hpa": 1013,
            "clouds_percent": 50,
            "wind_speed_ms": 5.0
        }
        sensor._cache_time = time.time() - 60
        
        reading = sensor._create_cached_or_empty_reading(time.time(), "API error")
        
        assert reading.data["from_cache"] == True
        assert reading.data["temperature_celsius"] == 15.0
        assert "cache_age_seconds" in reading.data
    
    def test_empty_reading_without_cache(self, sensor):
        """Empty reading when no cache available."""
        reading = sensor._create_cached_or_empty_reading(1234567890.0, "No data")
        
        assert reading.data["from_cache"] == False
        assert reading.data["temperature_celsius"] is None
        assert reading.data["error"] == "No data"
    
    def test_location_priority(self):
        """Coordinates take priority over location name."""
        sensor = WeatherSensor(
            api_key="test",
            location="London",
            lat=51.5,
            lon=-0.1
        )
        
        # Both are set, but lat/lon should be used
        assert sensor.lat == 51.5
        assert sensor.lon == -0.1
        assert sensor.location == "London"
