from typing import Any
import httpx
import os
import logging
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("weather-mcp")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8085"))
TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")

# Initialize FastMCP server
mcp = FastMCP("weather", host=HOST, port=PORT)

# Constants
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
USER_AGENT = "weather-app/1.0"

async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to the WeatherAPI with proper error handling."""
    # Check if API key is set
    api_key = os.getenv("WEATHERAPI_KEY")
    if not api_key:
        logger.error("WeatherAPI key not set. Set WEATHERAPI_KEY.")
        return None
        
    headers = {
        "User-Agent": USER_AGENT,
    }
    # Add API key to parameters
    params["key"] = api_key
    
    url = f"{WEATHERAPI_BASE}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("WeatherAPI returned HTTP %s: %s", e.response.status_code, e.response.text)
            return None
        except httpx.RequestError as e:
            logger.error("WeatherAPI request failed: %s", e)
            return None
        except Exception as e:
            logger.exception("Unexpected WeatherAPI error: %s", e)
            return None

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    params = {
        "q": city,
        "aqi": "no"
    }
    
    data = await make_weather_request("current.json", params)

    if not data:
        if not os.getenv("WEATHERAPI_KEY"):
            return f"❌ WeatherAPI key not configured. Please set WEATHERAPI_KEY environment variable with your API key from weatherapi.com"
        return f"Unable to fetch current weather data for {city}. Please check the city name and API key configuration."

    current = data["current"]
    location = data["location"]
    
    return f"""
Current Weather for {location['name']}, {location['region']}, {location['country']}:

Temperature: {current['temp_c']}°C ({current['temp_f']}°F)
Feels like: {current['feelslike_c']}°C ({current['feelslike_f']}°F)
Condition: {current['condition']['text']}
Humidity: {current['humidity']}%
Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}
Pressure: {current['pressure_mb']} mb
UV Index: {current['uv']}
Visibility: {current['vis_km']} km

Last updated: {current['last_updated']}
"""

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-3 for free tier, max 10 for paid)
    """
    # Limit days to 1–3 for the free tier.
    days = max(1, min(days, 3))
    
    params = {
        "q": city,
        "days": str(days),
        "aqi": "no",
        "alerts": "no"
    }
    
    data = await make_weather_request("forecast.json", params)

    if not data:
        if not os.getenv("WEATHERAPI_KEY"):
            return f"❌ WeatherAPI key not configured. Please set WEATHERAPI_KEY environment variable with your API key from weatherapi.com"
        return f"Unable to fetch forecast data for {city}. Please check the city name and API key configuration."

    location = data["location"]
    forecast_days = data["forecast"]["forecastday"]
    
    forecasts = []
    forecasts.append(f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}:")
    
    for day in forecast_days:
        day_data = day["day"]
        date = day["date"]
        
        forecast = f"""
{date}:
High: {day_data['maxtemp_c']}°C ({day_data['maxtemp_f']}°F)
Low: {day_data['mintemp_c']}°C ({day_data['mintemp_f']}°F)
Condition: {day_data['condition']['text']}
Chance of Rain: {day_data['daily_chance_of_rain']}%
Max Wind: {day_data['maxwind_kph']} km/h
UV Index: {day_data['uv']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    return "✅ Weather MCP Server is running and ready to provide worldwide weather data."

logger.info("MCP server initialized with %s transport", TRANSPORT)
logger.info("Available tools: get_current_weather, get_forecast, health_check")

if __name__ == "__main__":
    if TRANSPORT == "streamable-http":
        logger.info("Starting MCP server on http://%s:%s/mcp", HOST, PORT)
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting MCP server in stdio mode")
        mcp.run()