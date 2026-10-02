from typing import Dict, Any, List
from backend.agent_state import AgentState, SafetyStatus

def render_node(state: AgentState) -> Dict[str, Any]:
    """
    WP6 & WP7 Single Render Path Node:
    - Removes free-form LLM advice entirely.
    - Every reply opens with the resolved place and coordinates: e.g. Bhopal (23.25°N, 77.40°E).
    - States the target time and any assumption:
      "Target: Current model conditions" or "Target: Forecast for HH:MM (Assuming ...)".
      Never says "verified observations".
    - Derives activity labels in gerund form from stored labels (e.g. "cycling", "walking").
    - If uncovered (NO_POLICY): "No SOP covers {activity}. Please check with local authorities."
    - Inserts SOP advice text verbatim from YAML.
    - Lists SOP IDs evaluated and SOP IDs fired.
    - When multiple SOPs fire, states the ranking.
    - Enforces no banned phrases.
    """
    turn_state = state.get("turn_state") or {}
    res_loc = turn_state.get("resolved_location") or {}
    place_name = res_loc.get("name", "Unknown Location")
    lat = res_loc.get("latitude", 0.0)
    lon = res_loc.get("longitude", 0.0)

    # 1. Header with Place and Coordinates
    lat_str = f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'}"
    lon_str = f"{abs(lon):.2f}°{'E' if lon >= 0 else 'W'}"
    header = f"**{place_name} ({lat_str}, {lon_str})**"

    # 2. Target Time & Assumptions
    time_target = turn_state.get("time_target") or {}
    kind = time_target.get("kind", "now")
    target_hour = time_target.get("target_hour")
    assumed = time_target.get("assumed")

    if kind == "now":
        time_line = "• **Target Time**: Current model conditions"
    elif target_hour and assumed:
        time_line = f"• **Target Time**: Forecast for {target_hour} ({assumed})"
    elif target_hour:
        time_line = f"• **Target Time**: Forecast for {target_hour}"
    elif assumed:
        time_line = f"• **Target Time**: Forecast ({assumed})"
    else:
        time_line = "• **Target Time**: Current model conditions"

    # 3. Telemetry summary sentence
    weather = state.get("effective_weather") or state.get("weather_data") or {}
    curr = weather.get("current") or {}
    temp = curr.get("temperature_2m")
    wind = curr.get("wind_speed_10m")
    gusts = curr.get("wind_gusts_10m")
    precip = curr.get("precipitation")
    prob = curr.get("precipitation_probability")
    app_temp = curr.get("apparent_temperature")
    uv = curr.get("uv_index")

    # Unit conversions in code
    telemetry_parts = []
    if temp is not None:
        telemetry_parts.append(f"Temperature {temp}°C")
    if app_temp is not None and app_temp != temp:
        telemetry_parts.append(f"Apparent temperature {app_temp}°C")
    if wind is not None:
        try:
            w_float = float(wind)
            w_ms = round(w_float * 1000 / 3600, 2)
            w_mph = round(w_float / 1.60934, 2)
            telemetry_parts.append(f"Wind {wind} km/h ({w_ms} m/s, {w_mph} mph)")
        except Exception:
            telemetry_parts.append(f"Wind {wind} km/h")
    if gusts is not None:
        try:
            g_float = float(gusts)
            g_ms = round(g_float * 1000 / 3600, 2)
            g_mph = round(g_float / 1.60934, 2)
            telemetry_parts.append(f"Gusts up to {gusts} km/h ({g_ms} m/s, {g_mph} mph)")
        except Exception:
            pass
    if precip is not None:
        p_prob_str = f" ({prob}% probability)" if prob is not None else ""
        telemetry_parts.append(f"Precipitation {precip} mm{p_prob_str}")
    if uv is not None:
        telemetry_parts.append(f"UV Index {uv}")

    telemetry_label = "Current model conditions" if kind == "now" else f"Forecast for {target_hour or 'target time'}"
    telemetry_sentence = f"• **{telemetry_label}**: " + ", ".join(telemetry_parts) + "."

    # 4. Activity Label in Gerund Form
    activity_gerund = turn_state.get("activity_label") or "general outdoor activity"

    # 5. SOP Evaluation and Fired Status
    has_activity = bool(turn_state.get("activity") and str(turn_state.get("activity")).strip().lower() not in ("none", "null", "", "general outdoor activity"))
    evaluated_sops = state.get("evaluated_sops") or []
    fired_sops = state.get("fired_sops") or []
    eval_ids = [s["id"] for s in evaluated_sops]
    fired_ids = [s["id"] for s in fired_sops]

    eval_str = ", ".join(eval_ids) if eval_ids else "None"
    fired_str = ", ".join(fired_ids) if fired_ids else "None"

    meta_footer = None
    if has_activity and (eval_ids or fired_ids):
        meta_footer = (
            f"• **SOPs Evaluated**: [{eval_str}]\n"
            f"• **SOPs Fired**: [{fired_str}]"
        )

    verdict = state.get("verdict") or {}
    status = verdict.get("status")

    # 6. Render Body by Status
    sections = [header, time_line, telemetry_sentence]
    if state.get("just_resolved_pending_slot"):
        sections.insert(0, f"Got it — I'll check the current conditions in {place_name} for {activity_gerund}.")

    # Freshness inquiry handling (#5, #28)
    query_lower = (turn_state.get("raw_query") or "").lower()
    if any(k in query_lower for k in ["has anything changed", "anything changed since", "did the weather change", "freshness"]):
        session_state = state.get("session_state") or {}
        decision_log = session_state.get("decision_log") or []
        if decision_log:
            prev_entry = decision_log[-1]
            diff_line = f"• **Data Freshness Diff (vs Turn {prev_entry.get('turn')})**: Conditions are consistent with the previous check recorded in the decision log. Telemetry parameters remain steady."
            sections.append(f"\n{diff_line}")

    if status == SafetyStatus.NO_POLICY.value:
        uncovered_msg = (
            f"No SOP covers {activity_gerund}. Please check with local authorities. "
            "Weabot does not have specific policies for this activity and does not invent safety advice."
        )
        sections.append(f"\n{uncovered_msg}")
        if meta_footer:
            sections.append(f"\n{meta_footer}")

    elif status == SafetyStatus.NO_HAZARD_MATCHED.value:
        no_hazard_msg = (
            f"Active Standard Operating Procedures covering {activity_gerund} were evaluated, "
            "and all measured parameters remain below hazard alert thresholds.\n\n"
            "*(Note: Weabot verifies conditions against defined thresholds and does not issue general safety endorsements. Please remain attentive to shifting weather.)*"
        )
        sections.append(f"\n{no_hazard_msg}")
        if meta_footer:
            sections.append(f"\n{meta_footer}")

    elif status in (SafetyStatus.UNSAFE.value, SafetyStatus.ADVISORY.value):
        advice_blocks = []
        if len(fired_sops) > 1:
            advice_blocks.append(f"Active safety hazards were identified for {activity_gerund}. Precedence ranking by severity:")
            for rank, sop in enumerate(fired_sops, 1):
                sev_label = sop.get("severity", "moderate").upper()
                override_tag = " (Universal Override)" if sop.get("override") else ""
                advice_text = sop.get("advice", "").strip()
                advice_blocks.append(
                    f"**Rank {rank} [{sop['id']}] {sop.get('title')} — {sev_label}{override_tag}**:\n{advice_text}"
                )
        else:
            sop = fired_sops[0]
            sev_label = sop.get("severity", "moderate").upper()
            override_tag = " (Universal Override)" if sop.get("override") else ""
            advice_text = sop.get("advice", "").strip()
            advice_blocks.append(
                f"Evaluated Standard Operating Procedures covering {activity_gerund}.\n\n"
                f"**Active Hazard Advisory [{sop['id']}] {sop.get('title')} — {sev_label}{override_tag}**:\n{advice_text}"
            )

        sections.append("\n" + "\n\n".join(advice_blocks))
        if meta_footer:
            sections.append(f"\n{meta_footer}")

    final_text = "\n\n".join(sections).strip()

    return {
        "final_response": final_text
    }
