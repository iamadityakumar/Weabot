import asyncio
from typing import Dict, Any
from backend.agent_state import AgentState
from backend.weather_client import WeatherClient, GeocodingError

_weather_client = WeatherClient()

def get_weather_client() -> WeatherClient:
    return _weather_client

def check_location_present(state: AgentState) -> str:
    """Routing function after intake."""
    intent = state.get("extracted_intent") or {}
    location = intent.get("location")
    if not location or not str(location).strip():
        return "ask_location"
    return "resolve_location"

def ask_location_node(state: AgentState) -> Dict[str, Any]:
    """Deterministic prompt asking the user for their location."""
    activity = (state.get("extracted_intent") or {}).get("activity", "your activity")
    return {
        "final_response": (
            f"To provide accurate safety guidance for {activity} based on live weather conditions, "
            "please specify which city or town you will be in."
        ),
        "sop_citations": [],
        "error_message": None
    }

async def location_resolve_node(state: AgentState) -> Dict[str, Any]:
    """Resolve location text via Open-Meteo geocoding."""
    intent = state.get("extracted_intent") or {}
    location = intent.get("location")
    session_facts = dict(state.get("session_facts") or {})

    try:
        geo = await _weather_client.geocode(str(location))
        session_facts["location_name"] = geo["name"]
        session_facts["latitude"] = geo["latitude"]
        session_facts["longitude"] = geo["longitude"]
        return {
            "session_facts": session_facts,
            "error_message": None
        }
    except GeocodingError as e:
        return {
            "error_message": f"Unable to resolve location '{location}'. {str(e)}"
        }

def check_geocode_status(state: AgentState) -> str:
    """Routing function after geocoding."""
    if state.get("error_message"):
        return "failure"
    return "fetch_weather"
