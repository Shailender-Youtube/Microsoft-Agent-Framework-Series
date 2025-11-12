"""
MCP Weather Server for Scenario 1
==================================
This server provides weather-related tools to agents via the Model Context Protocol.

Tools Provided:
- get_weather: Get current weather for a location (worldwide)
- get_forecast: Get weather forecast for a location (worldwide)
- get_alerts: Get weather alerts (if available)

Uses Open-Meteo API (free, no API key required)
https://open-meteo.com/

Usage:
    python weather_server.py
"""

from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("weather-server")

# Constants
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "MAF-A2A-Weather-Server/1.0"

# Helper functions
async def make_api_request(url: str, params: dict = None) -> dict[str, Any] | None:
    """Make a request to weather APIs with proper error handling."""
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"HTTP Error: {e}")
            return None
        except Exception as e:
            print(f"Error making request: {e}")
            return None


async def geocode_city(city: str, country: str = "") -> tuple[float, float, str] | None:
    """
    Get coordinates for a city using Open-Meteo Geocoding API.
    
    Returns:
        Tuple of (latitude, longitude, full_location_name) or None
    """
    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    if country:
        params["country"] = country
    
    data = await make_api_request(GEOCODING_API, params)
    
    if not data or "results" not in data or not data["results"]:
        return None
    
    result = data["results"][0]
    lat = result["latitude"]
    lon = result["longitude"]
    name = result["name"]
    country_name = result.get("country", "")
    admin1 = result.get("admin1", "")
    
    full_name = f"{name}, {admin1}, {country_name}" if admin1 else f"{name}, {country_name}"
    
    return (lat, lon, full_name)


# MCP Tool: Get Weather Alerts
@mcp.tool()
async def get_alerts(city: str, country: str = "") -> str:
    """Get weather alerts/warnings for a location.
    
    Note: Open-Meteo provides basic weather warnings. For detailed alerts,
    use region-specific services.

    Args:
        city: City name (e.g., "Melbourne", "Sydney")
        country: Country name or code (optional, e.g., "Australia", "AU")
        
    Returns:
        String containing weather warnings if available
    """
    location = await geocode_city(city, country)
    if not location:
        return f"Unable to find location: {city}"
    
    lat, lon, full_name = location
    
    # Open-Meteo doesn't provide detailed alerts, but we can check for severe conditions
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m",
        "timezone": "auto"
    }
    
    data = await make_api_request(WEATHER_API, params)
    
    if not data:
        return f"Unable to fetch weather data for {full_name}"
    
    current = data.get("current", {})
    wind_speed = current.get("wind_speed_10m", 0)
    wind_gusts = current.get("wind_gusts_10m", 0)
    precipitation = current.get("precipitation", 0)
    
    warnings = []
    
    if wind_gusts > 60:
        warnings.append(f"⚠️ HIGH WIND WARNING: Wind gusts up to {wind_gusts} km/h")
    elif wind_speed > 40:
        warnings.append(f"⚠️ WIND ADVISORY: Winds {wind_speed} km/h")
    
    if precipitation > 20:
        warnings.append(f"⚠️ HEAVY RAIN: {precipitation} mm precipitation")
    
    if not warnings:
        return f"No active weather warnings for {full_name}"
    
    return f"Weather warnings for {full_name}:\n" + "\n".join(warnings)


# MCP Tool: Get Weather Forecast
@mcp.tool()
async def get_forecast(city: str, country: str = "", days: int = 5) -> str:
    """Get weather forecast for a location.

    Args:
        city: City name (e.g., "Melbourne", "London", "Tokyo")
        country: Country name or code (optional, helps with accuracy)
        days: Number of days to forecast (1-16, default 5)
        
    Returns:
        String containing detailed weather forecast
    """
    location = await geocode_city(city, country)
    if not location:
        return f"Unable to find location: {city}"
    
    lat, lon, full_name = location
    
    # Limit days to valid range
    days = max(1, min(days, 16))
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
        "timezone": "auto",
        "forecast_days": days
    }
    
    data = await make_api_request(WEATHER_API, params)
    
    if not data or "daily" not in data:
        return f"Unable to fetch forecast for {full_name}"
    
    daily = data["daily"]
    forecasts = []
    
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 
        73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Light showers",
        81: "Showers", 82: "Heavy showers", 85: "Light snow showers", 
        86: "Snow showers", 95: "Thunderstorm", 96: "Thunderstorm with hail"
    }
    
    for i in range(len(daily["time"])):
        date = daily["time"][i]
        temp_max = daily["temperature_2m_max"][i]
        temp_min = daily["temperature_2m_min"][i]
        precip = daily["precipitation_sum"][i]
        wind = daily["wind_speed_10m_max"][i]
        code = daily["weather_code"][i]
        conditions = weather_codes.get(code, "Unknown")
        
        forecast = f"""
📅 {date}:
🌡️ Temperature: {temp_min}°C - {temp_max}°C
🌤️ Conditions: {conditions}
💧 Precipitation: {precip} mm
💨 Max Wind: {wind} km/h
"""
        forecasts.append(forecast)
    
    return f"🌍 {days}-Day Forecast for {full_name}:\n" + "\n".join(forecasts)


# MCP Tool: Get Current Weather
@mcp.tool()
async def get_weather(city: str, country: str = "") -> str:
    """Get current weather conditions for any city worldwide.
    
    Uses Open-Meteo API for real-time weather data.

    Args:
        city: City name (e.g., "Melbourne", "Sydney", "London", "Tokyo")
        country: Country name or code (optional, e.g., "Australia", "AU")
        
    Returns:
        String containing current weather conditions
    """
    # Geocode the city to get coordinates
    location = await geocode_city(city, country)
    if not location:
        return f"Unable to find location: {city}. Please check the spelling or try adding a country."
    
    lat, lon, full_name = location
    
    # Get current weather data
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "timezone": "auto"
    }
    
    data = await make_api_request(WEATHER_API, params)
    
    if not data or "current" not in data:
        return f"Unable to fetch weather data for {full_name}"
    
    current = data["current"]
    
    # Weather code descriptions
    weather_codes = {
        0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅", 3: "Overcast ☁️",
        45: "Foggy 🌫️", 48: "Fog 🌫️", 51: "Light drizzle 🌦️", 53: "Drizzle 🌧️", 
        55: "Heavy drizzle 🌧️", 61: "Light rain 🌧️", 63: "Rain 🌧️", 65: "Heavy rain 🌧️",
        71: "Light snow ❄️", 73: "Snow ❄️", 75: "Heavy snow ❄️", 77: "Snow grains ❄️",
        80: "Light showers 🌦️", 81: "Showers 🌧️", 82: "Heavy showers 🌧️",
        85: "Light snow showers 🌨️", 86: "Snow showers 🌨️",
        95: "Thunderstorm ⛈️", 96: "Thunderstorm with hail ⛈️"
    }
    
    temp = current.get("temperature_2m", "N/A")
    feels_like = current.get("apparent_temperature", "N/A")
    humidity = current.get("relative_humidity_2m", "N/A")
    wind_speed = current.get("wind_speed_10m", "N/A")
    wind_dir = current.get("wind_direction_10m", "N/A")
    wind_gusts = current.get("wind_gusts_10m", "N/A")
    precipitation = current.get("precipitation", 0)
    cloud_cover = current.get("cloud_cover", "N/A")
    weather_code = current.get("weather_code", 0)
    conditions = weather_codes.get(weather_code, "Unknown")
    time = current.get("time", "N/A")
    
    return f"""
🌍 Current Weather for {full_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 Time: {time}
🌡️ Temperature: {temp}°C
🤚 Feels Like: {feels_like}°C
🌤️ Conditions: {conditions}
💧 Humidity: {humidity}%
☁️ Cloud Cover: {cloud_cover}%
💨 Wind: {wind_speed} km/h from {wind_dir}°
🌬️ Wind Gusts: {wind_gusts} km/h
🌧️ Precipitation: {precipitation} mm
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def main():
    """Run the MCP weather server."""
    port = int(os.getenv("MCP_WEATHER_SERVER_PORT", "8001"))
    
    print(f"🌤️  Starting Weather MCP Server on port {port}")
    print(f"📡 Server name: {mcp.name}")
    print(f"🔧 Available tools: get_weather, get_forecast, get_alerts")
    print(f"🚀 Server ready for agent connections...")
    
    # Run server with stdio transport (for local agent connections)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
