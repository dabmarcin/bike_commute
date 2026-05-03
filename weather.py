"""
Weather integration for BikeCommute Analytics
Fetches temperature, wind speed and direction from OpenWeatherMap API
"""
import requests
from datetime import datetime
from config import OPENWEATHER_API_KEY, HOME


class WeatherManager:
    def __init__(self):
        self.api_key = OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.home_lat = HOME["lat"]
        self.home_lon = HOME["lon"]

    def get_weather_at_time(self, timestamp):
        """
        Get weather data for a specific timestamp

        Args:
            timestamp: ISO format datetime string or datetime object

        Returns:
            dict with temp, wind_speed, wind_direction or None if error
        """
        try:
            # Parse timestamp if needed
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                dt = timestamp

            # OpenWeatherMap doesn't have historical data for free tier
            # We'll use current weather as approximation or cache weather data
            # For production, consider using paid API or pre-fetch weather

            params = {
                "lat": self.home_lat,
                "lon": self.home_lon,
                "appid": self.api_key,
                "units": "metric",  # Celsius
            }

            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()

            weather_info = {
                "temp": data.get("main", {}).get("temp"),
                "wind_speed": data.get("wind", {}).get("speed"),  # m/s
                "wind_direction": data.get("wind", {}).get("deg"),  # degrees 0-360
                "humidity": data.get("main", {}).get("humidity"),
                "description": data.get("weather", [{}])[0].get("main"),
            }

            return weather_info

        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather: {e}")
            return {
                "temp": None,
                "wind_speed": None,
                "wind_direction": None,
                "humidity": None,
                "description": None,
            }

    def get_weather_for_ride(self, ride_date):
        """
        Get weather for a specific ride date

        Args:
            ride_date: ISO format datetime string

        Returns:
            dict with weather metrics
        """
        return self.get_weather_at_time(ride_date)

    def convert_wind_speed_ms_to_kmh(self, wind_speed_ms):
        """Convert wind speed from m/s to km/h"""
        if wind_speed_ms is None:
            return None
        return wind_speed_ms * 3.6

    def get_wind_direction_name(self, direction_deg):
        """Convert wind direction in degrees to cardinal directions"""
        if direction_deg is None:
            return None

        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(direction_deg / 22.5) % 16
        return directions[index]


if __name__ == "__main__":
    # Test weather module
    manager = WeatherManager()

    # Get current weather
    weather = manager.get_weather_at_time(datetime.now())
    print(f"Temperature: {weather['temp']}°C")
    print(f"Wind Speed: {weather['wind_speed']} m/s ({manager.convert_wind_speed_ms_to_kmh(weather['wind_speed']):.1f} km/h)")
    print(f"Wind Direction: {weather['wind_direction']}° ({manager.get_wind_direction_name(weather['wind_direction'])})")
    print(f"Humidity: {weather['humidity']}%")
    print(f"Conditions: {weather['description']}")
