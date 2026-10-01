from typing import Dict, Any, List
from backend.agent_state import AgentState
from backend.nodes.weather import get_sops_engine

def match_sops_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates weather data against SOP conditions and extracted activity.
    Performs deterministic threshold checking and multi-SOP conflict ranking.
    """
    weather = state.get("weather_data") or {}
    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity")

    sops_engine = get_sops_engine()
    matched = sops_engine.find_matching_sops(weather, activity)
    citations = [s["id"] for s in matched]

    return {
        "matched_sops": matched,
        "sop_citations": citations
    }

def check_match_status(state: AgentState) -> str:
    """Routing function after SOP evaluation."""
    matched = state.get("matched_sops") or []
    if not matched:
        return "no_match"
    return "compose"
