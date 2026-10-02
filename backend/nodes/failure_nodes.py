from typing import Dict, Any
from backend.agent_state import AgentState, SafetyStatus

def location_fail_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles location resolution failures:
    - Missing location
    - Unresolvable location
    - Coordinates / Open-ocean
    - Devanagari limitation notice
    """
    turn_state = state.get("turn_state") or {}
    err_msg = turn_state.get("error_message") or "Could you tell me which city or town you'd like the weather safety check for?"

    status = SafetyStatus.REFUSED.value
    if turn_state.get("error_type") == "ask_activity" or "activity are you planning" in err_msg.lower() or "what outdoor activity" in err_msg.lower():
        title = "Activity Required"
        status = SafetyStatus.NO_POLICY.value
    elif "ocean" in err_msg.lower() or "coordinates" in err_msg.lower():
        title = "Ocean / Remote Coordinates Uncovered"
        status = SafetyStatus.NO_POLICY.value
    elif "could not resolve" in err_msg.lower() or "could not find that place" in err_msg.lower():
        title = "Location Resolution Failed"
    elif "devanagari" in err_msg.lower() or "latin" in err_msg.lower():
        title = "Script Limitation Notice"
    else:
        title = "Location Required"

    return {
        "final_response": err_msg,
        "sop_citations": [],
        "verdict": {
            "status": status,
            "title": title,
            "severity": "low",
            "summary": err_msg
        },
        "weather_data": None,
        "effective_weather": None,
        "api_source": None,
        "error_message": err_msg
    }

def needs_location_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles prompt for missing location:
    User asks a weather/safety question with an activity but no location.
    Bot asks: 'Which city or town would you like me to check?'
    """
    msg = "Which city or town would you like me to check?"
    return {
        "final_response": msg,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.REFUSED.value,
            "title": "Location Required",
            "severity": "low",
            "summary": msg
        },
        "weather_data": None,
        "effective_weather": None,
        "api_source": None,
        "error_message": msg,
        "awaiting_slot": "location"
    }

def needs_activity_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles prompt for missing activity:
    User asks with a location but no activity.
    Bot asks: 'What outdoor activity are you planning in {location}?'
    """
    loc = state.get("location") or (state.get("pending_request") or {}).get("location") or state.get("place_text") or "your location"
    msg = f"What outdoor activity are you planning in {loc}? Tell me what you'd like to do (e.g., cycling, walking, running, outdoor gathering), and I'll check live safety conditions for you."
    return {
        "final_response": msg,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.NO_POLICY.value,
            "title": "Activity Required",
            "severity": "low",
            "summary": f"What outdoor activity are you planning in {loc}?"
        },
        "weather_data": None,
        "effective_weather": None,
        "api_source": None,
        "error_message": msg,
        "awaiting_slot": "activity"
    }

def time_fail_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles temporal resolution failures:
    - Beyond 16-day forecast horizon (refused with no data shown).
    - Past time elapsed.
    """
    turn_state = state.get("turn_state") or {}
    err_msg = turn_state.get("error_message") or "Requested time target cannot be evaluated."

    return {
        "final_response": err_msg,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.REFUSED.value,
            "title": "Forecast Horizon Exceeded · Prediction Refused",
            "severity": "low",
            "summary": "Forecasts beyond 16-day horizon cannot be evaluated."
        },
        "error_message": err_msg
    }

def data_fail_node(state: AgentState) -> Dict[str, Any]:
    """
    WP2 & Target Graph Data Failure Node:
    - Handles weather API timeouts / 500 errors.
    - Handles coordinate verification mismatch (> 0.5°).
    - Handles null required telemetry metrics.
    Emits honest status: DATA_UNAVAILABLE.
    """
    turn_state = state.get("turn_state") or {}
    res_loc = turn_state.get("resolved_location") or {}
    place = res_loc.get("display") or res_loc.get("name") or "your location"
    err_msg = turn_state.get("error_message") or "Weather telemetry service unreachable or payload verification failed."

    response = (
        f"Weather telemetry is currently unavailable for **{place}**. "
        f"{err_msg} "
        "Because our safety guidelines strictly prohibit guessing unverified meteorological conditions, "
        "safety procedures cannot be evaluated. Please check local conditions or try again later."
    )

    return {
        "final_response": response,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.DATA_UNAVAILABLE.value,
            "title": "Weather Telemetry Unavailable · Service Offline",
            "severity": "low",
            "summary": err_msg
        },
        "error_message": err_msg
    }
