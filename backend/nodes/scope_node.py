from typing import Dict, Any
from backend.agent_state import AgentState, SafetyStatus

SCOPE_TEXT = (
    "I'm Weabot. I help with outdoor safety using live weather and our approved guidelines, "
    "so I can't help with that. Try asking about cycling conditions in Bhopal this evening, or a walk in your city."
)

def scope_node(state: AgentState) -> Dict[str, Any]:
    """
    Fix 3: Scope Boundary Node
    Deterministic fixed text for out-of-scope requests (code, stocks, recipes, general chat).
    Carries zero weather data and no card.
    """
    turn_state = state.get("turn_state") or {}
    query = (turn_state.get("raw_query") or state.get("user_message") or "").lower()

    if any(k in query for k in ["what should i wear", "what to wear", "clothing advice", "suggest an outfit"]):
        msg = (
            "Specific clothing or fashion recommendations are outside our safety advisory scope. "
            "Please check local forecast temperatures and dress comfortably for conditions."
        )
        title = "Out of Scope · Clothing Advice"
    elif any(k in query for k in ["air quality", "is the air fine", "air pollution", "aqi"]):
        msg = (
            "Weabot evaluates physical weather telemetry (temperature, wind, rain, UV) from numerical prediction models "
            "and does not monitor real-time air quality index (AQI) or provide medical advice. "
            "Please consult official air quality monitors or healthcare professionals for respiratory guidance."
        )
        title = "Out of Scope · Air Quality / Medical Guidance"
    elif any(k in query for k in ["has the imd issued", "imd issued a warning", "imd warning", "imd alert", "low-pressure system over mp"]):
        msg = (
            "Data Source Notice: Weabot is powered by physical telemetry from Open-Meteo numerical weather prediction models "
            "and does not have an active data integration with the India Meteorological Department (IMD) or national synoptic early-warning feeds. "
            "Because we cannot verify official government bulletins or synoptic warnings, we strictly refrain from guessing or inventing alerts. "
            "Please check https://mausam.imd.gov.in for official IMD alerts."
        )
        title = "Out of Scope · Synoptic Early Warning Feeds"
    else:
        msg = SCOPE_TEXT
        title = "Out of Scope"

    return {
        "final_response": msg,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.OUT_OF_SCOPE.value,
            "title": title,
            "severity": "low",
            "summary": "Request is outside Weabot outdoor activity safety scope."
        },
        "weather_data": None,
        "effective_weather": None,
        "api_source": None
    }
