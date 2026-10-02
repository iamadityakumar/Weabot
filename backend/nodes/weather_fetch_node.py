from typing import Dict, Any
from backend.agent_state import AgentState
from backend.nodes.location import get_weather_client
from backend.sops_engine import get_sops_engine
from backend.weather_client import WeatherAPIError

async def fetch_weather_node(state: AgentState) -> Dict[str, Any]:
    """
    Weather Fetch Node:
    Queries Open-Meteo with dynamic field aggregation and 16-day forecast horizon.
    """
    turn_state = dict(state.get("turn_state") or {})
    res_loc = turn_state.get("resolved_location") or {}
    lat = res_loc.get("latitude")
    lon = res_loc.get("longitude")

    if lat is None or lon is None:
        turn_state["error_type"] = "data_fail"
        turn_state["error_message"] = "Missing coordinates for weather fetch."
        return {"turn_state": turn_state}

    import time
    import urllib.parse
    from datetime import datetime, timezone

    city_name = res_loc.get("name") or "Unknown"
    encoded_city = urllib.parse.quote(city_name)
    geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=5&language=en&format=json"

    engine = get_sops_engine()
    required_fields = engine.get_required_weather_fields()
    current_param = ",".join(required_fields)
    forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current={current_param}&forecast_days=16&timezone=auto"
    time_target = turn_state.get("time_target") or {}

    # If weather_data was explicitly injected for test/mock, reuse it ONLY if coordinates match or are unspecified
    injected_weather = state.get("weather_data")
    is_valid_injection = False
    if injected_weather and isinstance(injected_weather, dict) and "current" in injected_weather:
        inj_lat = injected_weather.get("latitude")
        inj_lon = injected_weather.get("longitude")
        if inj_lat is not None and inj_lon is not None:
            if abs(float(inj_lat) - float(lat)) <= 0.5 and abs(float(inj_lon) - float(lon)) <= 0.5:
                is_valid_injection = True
        else:
            # Unbound synthetic fixture passed in invoke
            is_valid_injection = True

    if is_valid_injection:
        inj = dict(injected_weather)
        if inj.get("latitude") is None:
            inj["latitude"] = lat
            inj["longitude"] = lon
        if not inj.get("current_units"):
            inj["current_units"] = {
                "temperature_2m": "°C",
                "apparent_temperature": "°C",
                "precipitation": "mm",
                "wind_speed_10m": "km/h",
                "wind_gusts_10m": "km/h"
            }
        
        api_source = {
            "city": res_loc.get("display") or res_loc.get("name") or "Unknown",
            "country": res_loc.get("country"),
            "coordinates": {"latitude": lat, "longitude": lon},
            "timezone": res_loc.get("timezone", "UTC"),
            "elevation": inj.get("elevation", 0),
            "timing": {
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "target_time_display": time_target.get("display_target", "Current model conditions"),
                "target_hour": time_target.get("target_hour"),
                "target_date": time_target.get("target_date"),
                "assumed": time_target.get("assumed"),
                "response_time_ms": 0.5
            },
            "requests": {
                "geocoding": {
                    "method": "GET",
                    "url": geocoding_url,
                    "city_query": city_name
                },
                "forecast": {
                    "method": "GET",
                    "url": forecast_url,
                    "latitude": lat,
                    "longitude": lon,
                    "fields": required_fields
                }
            },
            "response_summary": {
                "status": 200,
                "current": inj.get("current", {})
            }
        }
        return {
            "weather_data": inj,
            "turn_state": turn_state,
            "api_source": api_source
        }

    weather_client = get_weather_client()
    t0 = time.perf_counter()

    try:
        payload = await weather_client.fetch_weather(lat, lon, required_fields)
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)

        api_source = {
            "city": res_loc.get("display") or res_loc.get("name") or "Unknown",
            "country": res_loc.get("country"),
            "coordinates": {"latitude": lat, "longitude": lon},
            "timezone": res_loc.get("timezone", payload.get("timezone", "UTC")),
            "elevation": payload.get("elevation"),
            "timing": {
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "target_time_display": time_target.get("display_target", "Current model conditions"),
                "target_hour": time_target.get("target_hour"),
                "target_date": time_target.get("target_date"),
                "assumed": time_target.get("assumed"),
                "response_time_ms": duration_ms
            },
            "requests": {
                "geocoding": {
                    "method": "GET",
                    "url": geocoding_url,
                    "city_query": city_name
                },
                "forecast": {
                    "method": "GET",
                    "url": forecast_url,
                    "latitude": lat,
                    "longitude": lon,
                    "fields": required_fields
                }
            },
            "response_summary": {
                "status": 200,
                "current": payload.get("current", {})
            }
        }

        return {
            "weather_data": payload,
            "turn_state": turn_state,
            "api_source": api_source
        }
    except WeatherAPIError as e:
        turn_state["error_type"] = "data_fail"
        turn_state["error_message"] = f"Weather telemetry service unreachable: {str(e)}"
        return {"turn_state": turn_state}
