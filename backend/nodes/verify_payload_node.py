from typing import Dict, Any
from backend.agent_state import AgentState
from backend.nodes.location import get_weather_client
from backend.sops_engine import get_sops_engine

def verify_payload_node(state: AgentState) -> Dict[str, Any]:
    """
    WP2 Payload Verification Node:
    - Checks response lat/lon is within about 0.5 of resolved coordinates.
    - Checks current_units match assumed units.
    - Checks required telemetry fields are non-null.
    - Resolves effective weather metrics for the requested TimeTarget (current vs hourly slice).
    """
    turn_state = dict(state.get("turn_state") or {})
    weather_data = state.get("weather_data") or {}
    res_loc = turn_state.get("resolved_location") or {}
    target_lat = res_loc.get("latitude", 0.0)
    target_lon = res_loc.get("longitude", 0.0)

    engine = get_sops_engine()
    required_fields = list(engine.get_required_weather_fields())
    weather_client = get_weather_client()

    valid, reason = weather_client.verify_payload(weather_data, target_lat, target_lon, required_fields)
    if not valid:
        turn_state["error_type"] = "data_fail"
        turn_state["error_message"] = f"Payload verification failed: {reason}"
        return {"turn_state": turn_state}

    # Extract target time weather metrics
    time_target = turn_state.get("time_target") or {}
    kind = time_target.get("kind", "now")
    iso_target = time_target.get("iso")
    
    effective_weather = dict(weather_data)
    curr_block = dict(weather_data.get("current") or {})
    
    if kind in ("hour", "day") and iso_target:
        hourly = weather_data.get("hourly") or {}
        times = hourly.get("time") or []
        if times and iso_target in times:
            idx = times.index(iso_target)
            target_slice = {}
            for k, v in hourly.items():
                if isinstance(v, list) and idx < len(v):
                    target_slice[k] = v[idx]
            target_slice["time"] = iso_target
            effective_weather["current"] = target_slice
        elif times:
            # Match by prefix (e.g. date + hour)
            target_prefix = iso_target[:13]  # YYYY-MM-DDTHH
            matched_idx = None
            for idx, t in enumerate(times):
                if t.startswith(target_prefix):
                    matched_idx = idx
                    break
            if matched_idx is not None:
                target_slice = {}
                for k, v in hourly.items():
                    if isinstance(v, list) and matched_idx < len(v):
                        target_slice[k] = v[matched_idx]
                target_slice["time"] = times[matched_idx]
                effective_weather["current"] = target_slice

    api_source = dict(state.get("api_source") or {})
    if effective_weather.get("current"):
        if api_source and "response_summary" in api_source:
            api_source["response_summary"] = dict(api_source["response_summary"])
            api_source["response_summary"]["current"] = effective_weather["current"]
        if api_source and "timing" in api_source:
            api_source["timing"] = dict(api_source["timing"])
            if iso_target:
                api_source["timing"]["evaluated_target_time"] = iso_target

    return {
        "effective_weather": effective_weather,
        "weather_data": effective_weather,
        "api_source": api_source,
        "turn_state": turn_state
    }
