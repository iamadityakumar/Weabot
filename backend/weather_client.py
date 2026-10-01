import httpx
from typing import Dict, Any, Optional, List
from backend.config import settings

class WeatherClientError(Exception):
    """Base exception for weather and geocoding operations."""
    pass

class GeocodingError(WeatherClientError):
    """Raised when location cannot be resolved."""
    pass

class WeatherAPIError(WeatherClientError):
    """Raised when weather forecast API fails, times out, or returns error."""
    pass

class WeatherClient:
    """
    Async client for Open-Meteo Geocoding & Forecast APIs.
    Features:
    - Dynamic field aggregation passed from SOPs engine.
    - Deterministic error classification for honest failure routing.
    - In-memory geocoding cache.
    - Simulation mode for eval testing (e.g. unreachable API).
    """

    def __init__(self):
        self.geocoding_url = settings.OPEN_METEO_GEOCODING_URL
        self.forecast_url = settings.OPEN_METEO_FORECAST_URL
        self._geocode_cache: Dict[str, Dict[str, Any]] = {}
        # Simulation flag for testing unreachable API (Eval E7)
        self.simulate_unreachable: bool = False

    async def geocode(self, city_name: str) -> Dict[str, Any]:
        """
        Resolve city name to {name, latitude, longitude, country, admin1}.
        Raises GeocodingError if not found, empty, or HTTP failure.
        """
        if not city_name or not city_name.strip():
            raise GeocodingError("City name is empty or not provided.")

        clean_name = city_name.strip().lower()
        if clean_name in self._geocode_cache:
            return self._geocode_cache[clean_name]

        params = {
            "name": city_name.strip(),
            "count": 5,
            "language": "en",
            "format": "json"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.geocoding_url, params=params)
                if resp.status_code != 200:
                    raise GeocodingError(f"Geocoding service returned HTTP {resp.status_code}")

                data = resp.json()
                results = data.get("results")
                if not results or len(results) == 0:
                    raise GeocodingError(f"Could not resolve location: '{city_name}'")

                # Default to first candidate
                top_match = results[0]
                resolved = {
                    "name": top_match.get("name", city_name),
                    "latitude": round(float(top_match["latitude"]), 4),
                    "longitude": round(float(top_match["longitude"]), 4),
                    "country": top_match.get("country", ""),
                    "admin1": top_match.get("admin1", ""),
                    "timezone": top_match.get("timezone", "UTC"),
                }
                self._geocode_cache[clean_name] = resolved
                return resolved

        except httpx.RequestError as e:
            raise GeocodingError(f"Geocoding network error: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise GeocodingError(f"Malformed geocoding response: {e}")

    async def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch current weather metrics from Open-Meteo.
        Requires explicit field list to prevent empty responses.
        Raises WeatherAPIError on HTTP failure, timeout, or simulation.
        """
        if self.simulate_unreachable:
            raise WeatherAPIError("Simulated Open-Meteo connection timeout / 500 error.")

        if not fields:
            fields = [
                "temperature_2m",
                "apparent_temperature",
                "precipitation",
                "precipitation_probability",
                "rain",
                "weather_code",
                "wind_speed_10m",
                "wind_gusts_10m",
                "uv_index",
                "relative_humidity_2m"
            ]

        # Comma-delimited list of fields for current parameter
        current_param = ",".join(fields)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": current_param,
            "timezone": "auto"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.forecast_url, params=params)
                if resp.status_code != 200:
                    raise WeatherAPIError(
                        f"Weather forecast service returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )

                data = resp.json()
                if "current" not in data or not isinstance(data["current"], dict):
                    raise WeatherAPIError("Invalid payload: 'current' weather block missing from API response.")

                return {
                    "latitude": data.get("latitude", latitude),
                    "longitude": data.get("longitude", longitude),
                    "timezone": data.get("timezone", "UTC"),
                    "elevation": data.get("elevation", 0),
                    "current": data["current"],
                    "current_units": data.get("current_units", {})
                }

        except httpx.RequestError as e:
            raise WeatherAPIError(f"Weather API network timeout/failure: {e}")
        except Exception as e:
            if isinstance(e, WeatherAPIError):
                raise e
            raise WeatherAPIError(f"Unexpected weather fetch error: {e}")
