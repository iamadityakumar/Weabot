import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from backend.agent_state import AgentState
from backend.nodes.weather import get_sops_engine

def match_sops_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates weather data against SOP conditions and extracted activity.
    Performs deterministic threshold checking and multi-SOP conflict ranking.
    Supports comprehensive time grounding (this weekend, Saturday, Sunday, in 3 days,
    tonight, tomorrow morning/2am), explicit past elapsed checks, and horizon limits.
    """
    weather = state.get("weather_data") or {}
    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity")
    time_window = intent.get("time_window", "current")

    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")
    query_lower = user_query.lower()

    # 1. Past elapsed time detection
    if any(k in query_lower for k in ["yesterday", "last night", "earlier today", "past weather", "two days ago"]):
        return {
            "matched_sops": [],
            "sop_citations": [],
            "effective_weather": weather,
            "weather_data": weather,
            "unverified_sops": [],
            "time_status": "PAST"
        }

    # 2. Horizon limit check (> 7-14 days)
    if time_window == "beyond_horizon" or any(k in query_lower for k in ["next month", "in 2 months", "in 30 days", "in a month"]):
        return {
            "matched_sops": [],
            "sop_citations": [],
            "effective_weather": weather,
            "weather_data": weather,
            "unverified_sops": [],
            "time_status": "HORIZON_EXCEEDED"
        }

    # 3. Time-aware weather snapshot resolution
    effective_weather = dict(weather)
    hourly = weather.get("hourly", {})
    times = hourly.get("time", [])

    eval_target_time = None
    eval_target_hour = None

    if times:
        curr_time_str = (weather.get("current") or {}).get("time", "")
        try:
            curr_dt = datetime.fromisoformat(curr_time_str) if curr_time_str else datetime.now(timezone.utc)
        except Exception:
            curr_dt = datetime.now(timezone.utc)

        target_date_str = None
        target_hour_str = None

        # Detect specific temporal expressions
        if "weekend" in query_lower or "this weekend" in query_lower:
            days_to_sat = (5 - curr_dt.weekday()) % 7
            if days_to_sat == 0 and curr_dt.hour >= 18:
                days_to_sat = 7
            target_dt = curr_dt + timedelta(days=days_to_sat)
            target_date_str = target_dt.strftime("%Y-%m-%d")
            target_hour_str = "12:00"
        elif "saturday" in query_lower:
            days_to_sat = (5 - curr_dt.weekday()) % 7
            if days_to_sat == 0 and curr_dt.hour >= 18:
                days_to_sat = 7
            target_dt = curr_dt + timedelta(days=days_to_sat)
            target_date_str = target_dt.strftime("%Y-%m-%d")
            target_hour_str = "12:00"
        elif "sunday" in query_lower:
            days_to_sun = (6 - curr_dt.weekday()) % 7
            if days_to_sun == 0 and curr_dt.hour >= 18:
                days_to_sun = 7
            target_dt = curr_dt + timedelta(days=days_to_sun)
            target_date_str = target_dt.strftime("%Y-%m-%d")
            target_hour_str = "12:00"
        elif "in 3 days" in query_lower or "in three days" in query_lower:
            target_dt = curr_dt + timedelta(days=3)
            target_date_str = target_dt.strftime("%Y-%m-%d")
            target_hour_str = "12:00"
        elif "in 2 days" in query_lower or "in two days" in query_lower:
            target_dt = curr_dt + timedelta(days=2)
            target_date_str = target_dt.strftime("%Y-%m-%d")
            target_hour_str = "12:00"
        elif "tomorrow" in query_lower or "tomorrow" in time_window:
            target_dt = curr_dt + timedelta(days=1)
            target_date_str = target_dt.strftime("%Y-%m-%d")
            if "8am" in query_lower or "8 am" in query_lower or "morning" in query_lower or time_window == "morning":
                target_hour_str = "08:00"
            elif "afternoon" in query_lower or time_window == "afternoon":
                target_hour_str = "14:00"
            elif "evening" in query_lower or time_window in ("evening", "tonight"):
                target_hour_str = "18:00"
            elif "noon" in query_lower or time_window == "noon":
                target_hour_str = "12:00"
            else:
                target_hour_str = "12:00"
        elif "2am" in query_lower or "2 am" in query_lower or time_window in ("2am", "2 am"):
            target_hour_str = "02:00"
            if curr_dt.hour >= 2:
                target_dt = curr_dt + timedelta(days=1)
                target_date_str = target_dt.strftime("%Y-%m-%d")
            else:
                target_date_str = curr_dt.strftime("%Y-%m-%d")
        elif "evening" in query_lower or "tonight" in query_lower or time_window in ("evening", "tonight"):
            target_date_str = curr_dt.strftime("%Y-%m-%d")
            target_hour_str = "18:00"
        elif "noon" in query_lower or time_window == "noon":
            target_date_str = curr_dt.strftime("%Y-%m-%d")
            target_hour_str = "12:00"
        elif "afternoon" in query_lower or time_window == "afternoon":
            target_date_str = curr_dt.strftime("%Y-%m-%d")
            target_hour_str = "14:00"
        elif "morning" in query_lower or time_window == "morning":
            target_date_str = curr_dt.strftime("%Y-%m-%d")
            target_hour_str = "08:00"

        if target_hour_str:
            target_idx = None
            # Match both date and hour if target_date_str is present
            if target_date_str:
                for idx, t in enumerate(times):
                    if t.startswith(target_date_str) and target_hour_str in t:
                        target_idx = idx
                        break

            # Fallback to first upcoming occurrence after curr_time_str
            if target_idx is None:
                for idx, t in enumerate(times):
                    if target_hour_str in t:
                        if curr_time_str and t <= curr_time_str:
                            continue
                        target_idx = idx
                        break

            # Secondary fallback if all upcoming were past
            if target_idx is None:
                for idx, t in enumerate(times):
                    if target_hour_str in t:
                        target_idx = idx
                        break

            if target_idx is not None:
                effective_current = {}
                for k, v in hourly.items():
                    if isinstance(v, list) and target_idx < len(v):
                        effective_current[k] = v[target_idx]
                effective_weather["current"] = effective_current
                eval_target_time = times[target_idx]
                eval_target_hour = target_hour_str
                effective_weather["eval_target_time"] = eval_target_time
                effective_weather["eval_target_hour"] = eval_target_hour

    sops_engine = get_sops_engine()
    matched = sops_engine.find_matching_sops(effective_weather, activity)
    unverified = sops_engine.get_unverified_sops(effective_weather, activity)
    citations = [s["id"] for s in matched]

    return {
        "matched_sops": matched,
        "sop_citations": citations,
        "effective_weather": effective_weather,
        "weather_data": effective_weather,
        "unverified_sops": unverified,
        "time_status": None
    }

def check_match_status(state: AgentState) -> str:
    """Routing function after SOP evaluation."""
    if state.get("time_status") in ("PAST", "HORIZON_EXCEEDED"):
        return "no_match"
    matched = state.get("matched_sops") or []
    if not matched:
        return "no_match"
    return "compose"
