import asyncio
from typing import Dict, Any
from backend.agent_state import AgentState
from backend.nodes.location import get_weather_client
from backend.sops_engine import SOPsEngine
from backend.weather_client import WeatherAPIError

_sops_engine = SOPsEngine()

def get_sops_engine() -> SOPsEngine:
    return _sops_engine

async def fetch_weather_node(state: AgentState) -> Dict[str, Any]:
    """
    Fetch live weather data from Open-Meteo with dynamic field aggregation.
    """
    session_facts = dict(state.get("session_facts") or {})
    lat = session_facts.get("latitude")
    lon = session_facts.get("longitude")

    if lat is None or lon is None:
        return {
            "error_message": "Missing geographic coordinates to query weather forecast."
        }

    # Dynamic Field Aggregation: collect all fields required by active SOPs
    required_fields = _sops_engine.get_required_weather_fields()
    weather_client = get_weather_client()

    try:
        weather_payload = await weather_client.fetch_weather(lat, lon, required_fields)
        session_facts["last_weather_snapshot"] = weather_payload.get("current")
        return {
            "weather_data": weather_payload,
            "session_facts": session_facts,
            "error_message": None
        }
    except WeatherAPIError as e:
        return {
            "error_message": f"Weather service unavailable: {str(e)}"
        }

def check_weather_status(state: AgentState) -> str:
    """Routing function after weather fetch."""
    if state.get("error_message"):
        return "failure"
    return "match_sops"
