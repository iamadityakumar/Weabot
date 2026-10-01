from typing import Dict, Any
from backend.agent_state import AgentState
from backend.llm_factory import llm_factory

def no_match_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic honest fallback when no SOP covers the user's scenario.
    The LLM is NEVER invoked here to ensure no advice is invented.
    """
    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity", "this activity")
    session_facts = state.get("session_facts") or {}
    location = session_facts.get("location_name") or intent.get("location") or "your area"

    weather = state.get("weather_data") or {}
    curr = weather.get("current", {})
    temp = curr.get("temperature_2m", "N/A")
    wind = curr.get("wind_speed_10m", "N/A")
    precip = curr.get("precipitation", "N/A")

    response_text = (
        f"We checked live weather conditions for **{location}** "
        f"(Temperature: {temp}°C, Wind: {wind} km/h, Precipitation: {precip} mm), "
        f"but our official safety guidelines do not have specific policies covering '{activity}' "
        "under these conditions.\n\n"
        "To ensure your safety, our system does not invent or assume safety guidance where no policy exists. "
        "Please exercise personal discretion and consult local authorities for specific guidelines."
    )

    return {
        "final_response": response_text,
        "sop_citations": [],
        "error_message": None
    }

def failure_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic failure handler for geocoding errors or unreachable weather APIs.
    Never attempts to synthesize synthetic forecasts.
    """
    err = state.get("error_message") or "An unexpected service error occurred."
    response_text = (
        f"⚠️ **Weather Service Error**: {err}\n\n"
        "Our safety policy strictly prohibits answering outdoor safety questions with estimated "
        "or unverified weather conditions. Please check your query or verify with direct meteorological sources."
    )

    return {
        "final_response": response_text,
        "sop_citations": [],
        "error_message": err
    }

def compose_node(state: AgentState) -> Dict[str, Any]:
    """
    Composes safety guidance grounded solely in matched SOPs and live weather numbers.
    """
    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")

    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity", "outdoor activity")
    session_facts = state.get("session_facts") or {}
    location = session_facts.get("location_name") or intent.get("location") or "your area"

    weather = state.get("weather_data") or {}
    matched_sops = state.get("matched_sops") or []

    composed_text = llm_factory.compose_response(
        user_query=user_query,
        activity=activity,
        location=location,
        weather=weather,
        matched_sops=matched_sops
    )

    citations = [s["id"] for s in matched_sops]

    return {
        "final_response": composed_text,
        "sop_citations": citations,
        "error_message": None
    }
