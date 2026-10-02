from typing import Dict, Any
from backend.agent_state import AgentState
from backend.time_resolver import resolve_time

def resolve_time_node(state: AgentState) -> Dict[str, Any]:
    """
    WP3 Time Resolver Node:
    Calls deterministic resolve_time using location's timezone.
    If target is beyond 16-day horizon -> routes to time_fail with no data shown.
    If target is in the past -> flags past condition.
    """
    turn_state = dict(state.get("turn_state") or {})
    res_loc = turn_state.get("resolved_location") or {}
    tz_name = res_loc.get("timezone", "UTC")
    place_name = res_loc.get("display") or res_loc.get("name") or "your location"

    raw_query = turn_state.get("raw_query", "")
    time_expr = turn_state.get("time_expression")
    is_followup = turn_state.get("is_followup", False)

    # Prior target from decision_log if follow-up
    prior_target = None
    session_state = state.get("session_state") or {}
    decision_log = session_state.get("decision_log") or []
    if decision_log:
        prior_target = decision_log[-1].get("time_target_raw")

    target = resolve_time(
        expression=time_expr,
        query=raw_query,
        tz_name=tz_name,
        is_followup=is_followup,
        prior_target=prior_target
    )

    turn_state["time_target"] = target.to_dict()

    if target.kind == "beyond_horizon":
        turn_state["error_type"] = "time_fail"
        turn_state["error_message"] = (
            f"Forecast horizon exceeded: You asked about conditions next month in {place_name}. "
            "Our models provide hourly forecasts only within a 16-day horizon. "
            "Safety guidance cannot be evaluated months in advance."
        )

    return {"turn_state": turn_state}
