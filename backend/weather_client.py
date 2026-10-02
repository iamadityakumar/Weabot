import time
from datetime import datetime, timezone
import httpx
from typing import Dict, Any, Optional, List, Tuple
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

class PayloadVerificationError(WeatherClientError):
    """Raised when payload fails coordinate verification or contains null metrics."""
    pass

# WP0 & WP2 Deterministic City Stubs
CITY_STUBS = {
    "bhopal": {
        "name": "Bhopal",
        "latitude": 23.2547,
        "longitude": 77.4029,
        "timezone": "Asia/Kolkata",
        "admin1": "Madhya Pradesh",
        "country": "India",
        "current": {
            "time": "2026-10-02T15:30",
            "interval": 900,
            "temperature_2m": 31.3,
            "apparent_temperature": 33.5,
            "precipitation": 0.0,
            "precipitation_probability": 0,
            "rain": 0.0,
            "weather_code": 0,
            "wind_speed_10m": 12.0,
            "wind_gusts_10m": 18.0,
            "uv_index": 4.5,
            "relative_humidity_2m": 45,
            "is_day": 1
        },
        "current_units": {
            "time": "iso8601",
            "interval": "seconds",
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
            "weather_code": "wmo code",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "uv_index": "",
            "relative_humidity_2m": "%",
            "is_day": ""
        }
    },
    "jaipur": {
        "name": "Jaipur",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "timezone": "Asia/Kolkata",
        "admin1": "Rajasthan",
        "country": "India",
        "current": {
            "time": "2026-10-02T15:30",
            "interval": 900,
            "temperature_2m": 28.5,
            "apparent_temperature": 29.0,
            "precipitation": 0.0,
            "precipitation_probability": 0,
            "rain": 0.0,
            "weather_code": 0,
            "wind_speed_10m": 15.0,
            "wind_gusts_10m": 22.0,
            "uv_index": 5.0,
            "relative_humidity_2m": 40,
            "is_day": 1
        },
        "current_units": {
            "time": "iso8601",
            "interval": "seconds",
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
            "weather_code": "wmo code",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "uv_index": "",
            "relative_humidity_2m": "%",
            "is_day": ""
        }
    },
    "auckland": {
        "name": "Auckland",
        "latitude": -36.8485,
        "longitude": 174.7633,
        "timezone": "Pacific/Auckland",
        "admin1": "Auckland",
        "country": "New Zealand",
        "current": {
            "time": "2026-10-02T23:00",
            "interval": 900,
            "temperature_2m": 16.0,
            "apparent_temperature": 15.0,
            "precipitation": 0.0,
            "precipitation_probability": 10,
            "rain": 0.0,
            "weather_code": 1,
            "wind_speed_10m": 24.0,
            "wind_gusts_10m": 35.0,
            "uv_index": 2.0,
            "relative_humidity_2m": 70,
            "is_day": 1
        },
        "current_units": {
            "time": "iso8601",
            "interval": "seconds",
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
            "weather_code": "wmo code",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "uv_index": "",
            "relative_humidity_2m": "%",
            "is_day": ""
        }
    },
    "springfield": {
        "name": "Springfield",
        "latitude": 39.7817,
        "longitude": -89.6501,
        "timezone": "America/Chicago",
        "admin1": "Illinois",
        "country": "United States",
        "current": {
            "time": "2026-10-02T05:00",
            "interval": 900,
            "temperature_2m": 19.5,
            "apparent_temperature": 19.5,
            "precipitation": 0.0,
            "precipitation_probability": 0,
            "rain": 0.0,
            "weather_code": 0,
            "wind_speed_10m": 9.0,
            "wind_gusts_10m": 14.0,
            "uv_index": 3.0,
            "relative_humidity_2m": 60,
            "is_day": 0
        },
        "current_units": {
            "time": "iso8601",
            "interval": "seconds",
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
            "weather_code": "wmo code",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "uv_index": "",
            "relative_humidity_2m": "%",
            "is_day": ""
        }
    },
    "chicago": {
        "name": "Chicago",
        "latitude": 41.8781,
        "longitude": -87.6298,
        "timezone": "America/Chicago",
        "admin1": "Illinois",
        "country": "United States",
        "current": {
            "time": "2026-10-02T15:30",
            "interval": 900,
            "temperature_2m": 16.0,
            "apparent_temperature": 15.5,
            "precipitation": 0.0,
            "precipitation_probability": 0,
            "rain": 0.0,
            "weather_code": 0,
            "wind_speed_10m": 20.0,
            "wind_gusts_10m": 32.4,
            "uv_index": 3.0,
            "relative_humidity_2m": 50,
            "is_day": 1
        },
        "current_units": {
            "time": "iso8601",
            "interval": "seconds",
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
            "weather_code": "wmo code",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "uv_index": "",
            "relative_humidity_2m": "%",
            "is_day": ""
        }
    },
    "delhi": {
        "name": "Delhi",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timezone": "Asia/Kolkata",
        "admin1": "Delhi",
        "country": "India",
        "current": {
            "time": "2026-10-02T15:30",
            "interval": 900,
            "temperature_2m": 29.0,
            "apparent_temperature": 30.0,
            "precipitation": 0.0,
            "precipitation_probability": 0,
            "rain": 0.0,
            "weather_code": 0,
            "wind_speed_10m": 10.0,
            "wind_gusts_10m": 15.0,
            "uv_index": 5.0,
            "relative_humidity_2m": 55,
            "is_day": 1
        },
        "current_units": {
            "time": "iso8601",
            "interval": "seconds",
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "rain": "mm",
            "weather_code": "wmo code",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "uv_index": "",
            "relative_humidity_2m": "%",
            "is_day": ""
        }
    }
}

class WeatherClient:
    """
    Async client for Open-Meteo Geocoding & Forecast APIs.
    WP2 Compliance:
    - Cache key is (lat, lon, fetched_at bucket) with 10-minute TTL.
    - Refetch on any location change.
    - 16-day forecast horizon + hourly telemetry.
    - Verification of coordinates, units, and non-null required fields.
    """

    def __init__(self):
        self.geocoding_url = settings.OPEN_METEO_GEOCODING_URL
        self.forecast_url = settings.OPEN_METEO_FORECAST_URL
        self._geocode_cache: Dict[str, Dict[str, Any]] = {}
        # Cache keyed by (round(lat, 2), round(lon, 2), time_bucket_10min)
        self._weather_cache: Dict[Tuple[float, float, int], Dict[str, Any]] = {}
        self.simulate_unreachable: bool = False
        self.use_city_stubs: bool = False

    async def geocode(self, city_name: str) -> Dict[str, Any]:
        """
        Resolve city name to {name, latitude, longitude, country, admin1, timezone}.
        Raises GeocodingError if not found, empty, or HTTP failure.
        """
        if not city_name or not city_name.strip():
            raise GeocodingError("City name is empty or not provided.")

        clean_name = city_name.strip().lower()
        if clean_name in self._geocode_cache:
            return self._geocode_cache[clean_name]

        # Check known city stubs first if enabled
        if self.use_city_stubs and clean_name in CITY_STUBS:
            stub = CITY_STUBS[clean_name]
            resolved = {
                "name": stub["name"],
                "latitude": stub["latitude"],
                "longitude": stub["longitude"],
                "country": stub["country"],
                "admin1": stub["admin1"],
                "timezone": stub["timezone"]
            }
            self._geocode_cache[clean_name] = resolved
            return resolved

        # Raw coordinate check: e.g. "23.25, 77.41"
        coord_match = re_coords = None
        import re
        coord_match = re.match(r"^[-+]?([1-8]?\d(?:\.\d+)?|90(?:\.0+)?),\s*[-+]?(180(?:\.0+)?|(?:1[0-7]\d|\d{1,2})(?:\.\d+)?)$", city_name.strip())
        if coord_match:
            lat = round(float(coord_match.group(1)), 4)
            lon = round(float(coord_match.group(2)), 4)
            resolved = {
                "name": f"{lat}, {lon}",
                "latitude": lat,
                "longitude": lon,
                "country": "Coordinates",
                "admin1": "Direct Coordinates",
                "timezone": "UTC"
            }
            self._geocode_cache[clean_name] = resolved
            return resolved

        hits = await self.geocode_hits(city_name, count=5)
        if not hits:
            raise GeocodingError(f"Could not resolve location: '{city_name}'")
        resolved = hits[0]
        self._geocode_cache[clean_name] = resolved
        return resolved

    async def geocode_hits(self, city_name: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Query Open-Meteo for candidate hits (up to count) to support similarity ranking.
        """
        if not city_name or not city_name.strip():
            return []

        clean_name = city_name.strip().lower()

        # Check known city stubs first if enabled
        if self.use_city_stubs and clean_name in CITY_STUBS:
            stub = CITY_STUBS[clean_name]
            return [{
                "name": stub["name"],
                "latitude": stub["latitude"],
                "longitude": stub["longitude"],
                "country": stub["country"],
                "admin1": stub["admin1"],
                "timezone": stub["timezone"]
            }]

        params = {
            "name": city_name.strip(),
            "count": count,
            "language": "en",
            "format": "json"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.geocoding_url, params=params)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                results = data.get("results")
                if not results or len(results) == 0:
                    return []

                hits = []
                for r in results:
                    hits.append({
                        "name": r.get("name", city_name),
                        "latitude": round(float(r["latitude"]), 4),
                        "longitude": round(float(r["longitude"]), 4),
                        "country": r.get("country", ""),
                        "admin1": r.get("admin1", ""),
                        "timezone": r.get("timezone", "UTC"),
                    })
                return hits

        except Exception:
            return []

    async def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch weather from Open-Meteo with:
        - 10-minute location-keyed caching: (round(lat, 2), round(lon, 2), time_bucket_10min)
        - 16-day forecast horizon + hourly fields
        - Stub support for Bhopal, Jaipur, Auckland, Springfield
        """
        if self.simulate_unreachable:
            raise WeatherAPIError("Simulated Open-Meteo connection timeout / 500 error.")

        # Location-keyed 10-minute bucket: time.time() // 600
        time_bucket = int(time.time() // 600)
        cache_key = (round(latitude, 2), round(longitude, 2), time_bucket)

        if cache_key in self._weather_cache:
            return self._weather_cache[cache_key]

        # Check city stubs if enabled
        if self.use_city_stubs:
            for city_key, stub in CITY_STUBS.items():
                if abs(stub["latitude"] - latitude) < 0.2 and abs(stub["longitude"] - longitude) < 0.2:
                    payload = self._build_stub_payload(stub)
                    self._weather_cache[cache_key] = payload
                    return payload

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
                "relative_humidity_2m",
                "is_day"
            ]

        current_param = ",".join(fields)
        hourly_fields = [
            "temperature_2m",
            "apparent_temperature",
            "precipitation",
            "precipitation_probability",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "wind_gusts_10m",
            "uv_index",
            "relative_humidity_2m",
            "is_day"
        ]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": current_param,
            "hourly": ",".join(hourly_fields),
            "forecast_days": 16,  # 16-day horizon per WP3
            "timezone": "auto"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.forecast_url, params=params)
                if resp.status_code != 200:
                    raise WeatherAPIError(
                        f"Weather forecast service returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )

                data = resp.json()
                if "current" not in data or not isinstance(data["current"], dict):
                    raise WeatherAPIError("Invalid payload: 'current' weather block missing from API response.")

                payload = {
                    "latitude": data.get("latitude", latitude),
                    "longitude": data.get("longitude", longitude),
                    "timezone": data.get("timezone", "UTC"),
                    "elevation": data.get("elevation", 0),
                    "current": data["current"],
                    "current_units": data.get("current_units", {}),
                    "hourly": data.get("hourly", {})
                }
                self._weather_cache[cache_key] = payload
                return payload

        except httpx.RequestError as e:
            raise WeatherAPIError(f"Weather API network timeout/failure: {e}")
        except Exception as e:
            if isinstance(e, WeatherAPIError):
                raise e
            raise WeatherAPIError(f"Unexpected weather fetch error: {e}")

    def _build_stub_payload(self, stub: Dict[str, Any]) -> Dict[str, Any]:
        """Construct full 16-day hourly series for deterministic city stubs."""
        from datetime import datetime, timedelta
        import zoneinfo

        tz_str = stub["timezone"]
        try:
            tz = zoneinfo.ZoneInfo(tz_str)
        except Exception:
            tz = timezone.utc
        start_dt = datetime.now(tz).replace(minute=0, second=0, microsecond=0)

        hours_count = 16 * 24
        times = []
        temps = []
        apparents = []
        winds = []
        gusts = []
        precips = []
        probs = []
        uvs = []
        codes = []
        humidity = []
        is_days = []

        curr = stub["current"]
        base_temp = curr["temperature_2m"]
        base_app = curr["apparent_temperature"]
        base_wind = curr["wind_speed_10m"]
        base_gust = curr["wind_gusts_10m"]
        base_precip = curr["precipitation"]
        base_prob = curr["precipitation_probability"]
        base_uv = curr["uv_index"]

        for h in range(hours_count):
            t = start_dt + timedelta(hours=h)
            times.append(t.strftime("%Y-%m-%dT%H:00"))
            hour_of_day = t.hour
            is_day = 1 if 6 <= hour_of_day <= 18 else 0
            is_days.append(is_day)
            
            # Simple diurnal variation for hourly telemetry
            temp_var = 4.0 if 12 <= hour_of_day <= 16 else (-3.0 if hour_of_day <= 6 else 0.0)
            temps.append(round(base_temp + temp_var, 1))
            apparents.append(round(base_app + temp_var, 1))
            winds.append(base_wind)
            gusts.append(base_gust)
            precips.append(base_precip)
            probs.append(base_prob)
            uvs.append(base_uv if 11 <= hour_of_day <= 15 else 0.0)
            codes.append(0)
            humidity.append(50)

        return {
            "latitude": stub["latitude"],
            "longitude": stub["longitude"],
            "timezone": stub["timezone"],
            "elevation": 500,
            "current": curr,
            "current_units": stub["current_units"],
            "hourly": {
                "time": times,
                "temperature_2m": temps,
                "apparent_temperature": apparents,
                "wind_speed_10m": winds,
                "wind_gusts_10m": gusts,
                "precipitation": precips,
                "precipitation_probability": probs,
                "uv_index": uvs,
                "weather_code": codes,
                "relative_humidity_2m": humidity,
                "is_day": is_days
            }
        }

    def verify_payload(
        self,
        payload: Dict[str, Any],
        target_lat: float,
        target_lon: float,
        required_fields: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        WP2 Payload Verification:
        1. Checks response lat/lon is within 0.5 of resolved coordinates.
        2. Checks current_units match assumptions:
           - temperature_2m in °C
           - wind_speed_10m in km/h
           - precipitation in mm
        3. Checks required fields are non-null in current block.
        """
        if not payload or not isinstance(payload, dict):
            return False, "Payload is empty or non-dictionary."

        res_lat = payload.get("latitude")
        res_lon = payload.get("longitude")
        if res_lat is None or res_lon is None:
            return False, "Payload missing geographic coordinates."

        # Grid snapping tolerance check: within ~0.5 degree
        lat_diff = abs(float(res_lat) - float(target_lat))
        lon_diff = abs(float(res_lon) - float(target_lon))
        if lat_diff > 0.5 or lon_diff > 0.5:
            return False, f"Coordinate mismatch: resolved ({target_lat}, {target_lon}) vs payload ({res_lat}, {res_lon}) exceeds 0.5°."

        # Units verification
        units = payload.get("current_units") or {}
        if "temperature_2m" in units and units["temperature_2m"] not in ("°C", "°c", "C", "c"):
            return False, f"Unit mismatch for temperature_2m: expected °C, got {units['temperature_2m']}."
        if "wind_speed_10m" in units and units["wind_speed_10m"] not in ("km/h", "kmh"):
            return False, f"Unit mismatch for wind_speed_10m: expected km/h, got {units['wind_speed_10m']}."
        if "precipitation" in units and units["precipitation"] not in ("mm", "millimeters", "millimeter"):
            return False, f"Unit mismatch for precipitation: expected mm, got {units['precipitation']}."

        # Required fields non-null check
        curr = payload.get("current") or {}
        fields_to_check = required_fields or [
            "temperature_2m", "apparent_temperature", "wind_speed_10m", "precipitation"
        ]
        null_fields = []
        for f in fields_to_check:
            if f in curr and curr[f] is None:
                null_fields.append(f)

        if null_fields:
            return False, f"Required weather telemetry fields returned null: {', '.join(null_fields)}."

        return True, None
