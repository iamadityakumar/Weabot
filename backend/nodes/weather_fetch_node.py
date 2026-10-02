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

    # If weather_data was directly injected for test/mock, reuse it
    injected_weather = state.get("weather_data")
    if injected_weather and isinstance(injected_weather, dict) and "current" in injected_weather:
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
        return {
            "weather_data": inj,
            "turn_state": turn_state
        }

    engine = get_sops_engine()
    required_fields = engine.get_required_weather_fields()
    weather_client = get_weather_client()

    try:
        payload = await weather_client.fetch_weather(lat, lon, required_fields)
        return {
            "weather_data": payload,
            "turn_state": turn_state
        }
    except WeatherAPIError as e:
        turn_state["error_type"] = "data_fail"
        turn_state["error_message"] = f"Weather telemetry service unreachable: {str(e)}"
        return {"turn_state": turn_state}
