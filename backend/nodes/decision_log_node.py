from typing import Dict, Any, List
from backend.agent_state import AgentState

def log_decision_node(state: AgentState) -> Dict[str, Any]:
    """
    WP1 & WP2 Decision Log Node:
    - Appends audited turn record to SessionState.decision_log.
    - Stores raw numbers from the first answer to support deterministic diffing (fixing #5, #28).
    - Updates SessionState:
      - last_good_location (only on verified successful completion)
      - last_activity
      - last_subject
    """
    turn_state = state.get("turn_state") or {}
    session_state = dict(state.get("session_state") or {})
    decision_log: List[Dict[str, Any]] = list(session_state.get("decision_log") or [])

    res_loc = turn_state.get("resolved_location")
    activity = turn_state.get("activity_label") or turn_state.get("activity") or "general outdoor activity"
    subject = turn_state.get("subject", "adult")
    time_target = turn_state.get("time_target") or {}

    evaluated_sops = [s["id"] for s in state.get("evaluated_sops") or []]
    fired_sops = [s["id"] for s in state.get("fired_sops") or []]
    verdict = state.get("verdict") or {}
    final_response = state.get("final_response", "")

    # Telemetry snapshot numbers for diffing in future turns (#5, #28)
    weather_data = state.get("effective_weather") or state.get("weather_data") or {}
    curr = weather_data.get("current") or {}
    telemetry_numbers = {
        "temperature_2m": curr.get("temperature_2m"),
        "apparent_temperature": curr.get("apparent_temperature"),
        "wind_speed_10m": curr.get("wind_speed_10m"),
        "wind_gusts_10m": curr.get("wind_gusts_10m"),
        "precipitation": curr.get("precipitation"),
        "precipitation_probability": curr.get("precipitation_probability"),
        "uv_index": curr.get("uv_index")
    }

    # If this turn was a freshness inquiry ("has anything changed since you last checked"),
    # diff the new telemetry against the previous decision_log entry!
    query_lower = (turn_state.get("raw_query") or "").lower()
    if any(k in query_lower for k in ["has anything changed", "anything changed since", "did the weather change", "freshness"]):
        if decision_log:
            prev_entry = decision_log[-1]
            prev_nums = prev_entry.get("telemetry_numbers") or {}
            diffs = []
            for metric in ["temperature_2m", "wind_speed_10m", "precipitation"]:
                curr_v = telemetry_numbers.get(metric)
                prev_v = prev_nums.get(metric)
                if curr_v is not None and prev_v is not None:
                    delta = round(float(curr_v) - float(prev_v), 2)
                    diffs.append(f"{metric}: {curr_v} (earlier: {prev_v}, diff: {delta})")
            
            diff_summary = f"\n\n• **Data Freshness Diff (vs Turn {prev_entry.get('turn')})**: " + (", ".join(diffs) if diffs else "No variation detected across telemetry parameters.")
            final_response = final_response + diff_summary

    turn_number = len(decision_log) + 1
    new_entry = {
        "turn": turn_number,
        "place": res_loc.get("display") or res_loc.get("name") if res_loc else "Unknown",
        "coordinates": (res_loc.get("latitude"), res_loc.get("longitude")) if res_loc else None,
        "time_target": time_target.get("display_target", "Current model conditions"),
        "time_target_raw": time_target,
        "activity": activity,
        "subject": subject,
        "evaluated_sops": evaluated_sops,
        "fired_sops": fired_sops,
        "verdict": verdict.get("title", ""),
        "status": verdict.get("status", ""),
        "severity": verdict.get("severity", "low"),
        "telemetry_numbers": telemetry_numbers,
        "response_quote": final_response[:250]
    }
    decision_log.append(new_entry)

    # State Hygiene: update SessionState with verified good context
    session_state["decision_log"] = decision_log
    if res_loc:
        session_state["last_good_location"] = res_loc
    if activity:
        session_state["last_activity"] = activity
    if subject:
        session_state["last_subject"] = subject

    # Update legacy session_facts for UI / API client compatibility
    session_facts = dict(state.get("session_facts") or {})
    if res_loc:
        session_facts["location_name"] = res_loc.get("name")
        session_facts["location_display"] = res_loc.get("display")
        session_facts["latitude"] = res_loc.get("latitude")
        session_facts["longitude"] = res_loc.get("longitude")
    session_facts["activity"] = activity
    session_facts["subject"] = subject
    session_facts["last_weather_snapshot"] = curr
    session_facts["last_verdict_title"] = verdict.get("title")

    return {
        "final_response": final_response,
        "session_state": session_state,
        "session_facts": session_facts
    }
