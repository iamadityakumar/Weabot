from typing import Dict, Any
from backend.agent_state import AgentState, SafetyStatus

def scope_node(state: AgentState) -> Dict[str, Any]:
    """
    Scope Boundary Node:
    Deterministic answers for out-of-scope categories:
    - Financial investments / stock inquiries (Tesla)
    - Personal clothing / fashion advice
    - Air Quality Index (AQI) / Medical advice (Asthma)
    - Extreme high-altitude mountaineering (Everest)
    - Synoptic tracking / IMD early warnings
    """
    turn_state = state.get("turn_state") or {}
    query = (turn_state.get("raw_query") or "").lower()

    if any(k in query for k in ["tesla", "stock", "shares", "crypto", "bitcoin", "invest"]):
        msg = (
            "Financial and stock investment advice is completely outside operational scope. "
            "Weabot is strictly dedicated to evaluating outdoor activity safety using live meteorological data."
        )
        title = "Out of Scope · Financial Advice"
    elif any(k in query for k in ["what should i wear", "what to wear", "clothing advice", "suggest an outfit"]):
        msg = (
            "Specific clothing or fashion recommendations are outside our safety advisory scope. "
            "Please check local forecast temperatures and dress comfortably for conditions."
        )
        title = "Out of Scope · Clothing Advice"
    elif any(k in query for k in ["asthma", "air quality", "aqi fine for a jog", "fine for asthma"]):
        msg = (
            "Weabot evaluates physical weather telemetry (temperature, wind, rain, UV) from numerical prediction models "
            "and does not monitor real-time air quality index (AQI) or provide medical advice. "
            "Please consult official air quality monitors or healthcare professionals for respiratory guidance."
        )
        title = "Out of Scope · Air Quality / Medical Guidance"
    elif any(k in query for k in ["everest", "mount everest", "k2", "annapurna"]):
        msg = (
            "High-altitude extreme mountaineering safety is outside operational scope. "
            "Standard Operating Procedures cover municipal and regional outdoor recreation, not alpine expeditions."
        )
        title = "Out of Scope · Extreme Mountaineering"
    elif any(k in query for k in ["has the imd issued", "imd issued a warning", "imd warning", "imd alert", "low-pressure system over mp"]):
        msg = (
            "Data Source Notice: Weabot is powered by physical telemetry from Open-Meteo numerical weather prediction models "
            "and does not have an active data integration with the India Meteorological Department (IMD) or national synoptic early-warning feeds. "
            "Because we cannot verify official government bulletins or synoptic warnings, we strictly refrain from guessing or inventing alerts. "
            "Please check https://mausam.imd.gov.in for official IMD alerts."
        )
        title = "Out of Scope · Synoptic Early Warning Feeds"
    else:
        msg = "This request is outside the operational scope of the Outdoor Activity Safety Advisor."
        title = "Out of Scope"

    return {
        "final_response": msg,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.OUT_OF_SCOPE.value,
            "title": title,
            "severity": "low",
            "summary": "Request is outside operational scope."
        }
    }
