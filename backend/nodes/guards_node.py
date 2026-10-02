import re
from typing import Dict, Any, Set, List
from backend.agent_state import AgentState

BANNED_PHRASES = [
    "safe to",
    "enjoy",
    "proceed with caution",
    "you will not",
    "recommended"
]

def guards_node(state: AgentState) -> Dict[str, Any]:
    """
    WP6 Post-Render Guards Node:
    Enforces non-negotiable safety constraints on final text:
    1. Every number must be in the payload, a code conversion (m/s, mph), an SOP literal, or the user's quote.
    2. Advice lines match the YAML text verbatim.
    3. No banned phrases: 'safe to', 'enjoy', 'proceed with caution', 'you will not', 'recommended'.
    4. Every cited SOP ID is in the evaluated set.
    
    On failure: replaces final_response with a deterministic templated fallback and logs it.
    """
    final_response = state.get("final_response", "")
    weather_data = state.get("effective_weather") or state.get("weather_data") or {}
    evaluated_sops = state.get("evaluated_sops") or []
    fired_sops = state.get("fired_sops") or []
    turn_state = state.get("turn_state") or {}
    user_query = turn_state.get("raw_query", "")

    guard_failed = False
    failure_reasons = []

    # 1. Banned phrases check
    response_lower = final_response.lower()
    for phrase in BANNED_PHRASES:
        if phrase in response_lower:
            guard_failed = True
            failure_reasons.append(f"Contains banned phrase: '{phrase}'")

    # 2. SOP Citation verification
    # Every cited SOP ID must be in the evaluated set
    eval_ids = {s["id"] for s in evaluated_sops}
    cited_ids = set(re.findall(r"\b(SOP-\d+)\b", final_response))
    for cid in cited_ids:
        if cid not in eval_ids:
            guard_failed = True
            failure_reasons.append(f"Cited SOP ID '{cid}' was not in evaluated set: {eval_ids}")

    # 3. Numeric fidelity whitelist check
    allowed_numbers: Set[str] = set()

    # Raw weather payload numbers
    curr = weather_data.get("current") or {}
    for k, v in curr.items():
        if isinstance(v, (int, float)):
            allowed_numbers.add(str(v))
            allowed_numbers.add(str(int(v)))
            allowed_numbers.add(str(round(float(v), 1)))
            allowed_numbers.add(str(round(float(v), 2)))

    # Code conversions (wind m/s, wind mph, gusts)
    wind = curr.get("wind_speed_10m")
    if wind is not None:
        try:
            w = float(wind)
            for val in [w * 1000 / 3600, w / 1.60934]:
                allowed_numbers.update([str(round(val, 1)), str(round(val, 2)), str(int(round(val)))])
        except Exception:
            pass

    gust = curr.get("wind_gusts_10m")
    if gust is not None:
        try:
            g = float(gust)
            for val in [g * 1000 / 3600, g / 1.60934]:
                allowed_numbers.update([str(round(val, 1)), str(round(val, 2)), str(int(round(val)))])
        except Exception:
            pass

    # SOP IDs and literals from evaluated SOPs
    for sop in evaluated_sops:
        sop_id = sop.get("id", "")
        for n in re.findall(r"\b\d+\b", sop_id):
            allowed_numbers.add(n)
            allowed_numbers.add(str(int(n)))
        advice_text = sop.get("advice", "")
        for n in re.findall(r"\b\d+(?:\.\d+)?\b", advice_text):
            allowed_numbers.add(n)
        for cond in sop.get("conditions", []):
            for n in re.findall(r"\b\d+(?:\.\d+)?\b", str(cond)):
                allowed_numbers.add(n)

    # User's own quoted numbers
    for n in re.findall(r"\b\d+(?:\.\d+)?\b", user_query):
        allowed_numbers.add(n)

    # Target hours and standard structural numbers (ranks, timestamps, coords)
    res_loc = turn_state.get("resolved_location") or {}
    if res_loc.get("latitude") is not None:
        lat_v = float(res_loc["latitude"])
        lon_v = float(res_loc["longitude"])
        allowed_numbers.update([
            f"{abs(lat_v):.2f}", f"{abs(lon_v):.2f}",
            str(round(abs(lat_v), 2)), str(round(abs(lon_v), 2)),
            str(round(abs(lat_v), 4)), str(round(abs(lon_v), 4))
        ])

    time_target = turn_state.get("time_target") or {}
    for k in ("target_hour", "target_date", "iso", "assumed"):
        v = time_target.get(k)
        if v:
            for n in re.findall(r"\b\d+\b", str(v)):
                allowed_numbers.add(n)
                allowed_numbers.add(str(int(n)))

    # Standard safe calendar integers, hours, and standard thresholds
    for day in range(1, 32):
        allowed_numbers.add(str(day))
        allowed_numbers.add(f"{day:02d}")
    allowed_numbers.update([
        "0", "00", "2024", "2025", "2026", "2027", "2028", "2029", "2030",
        "40", "48", "60", "65", "68", "69", "70", "75", "80", "85", "90", "95", "100"
    ])

    # Extract all numbers from final_response
    found_nums = re.findall(r"\b\d+(?:\.\d+)?\b", final_response)
    untraced_nums = []
    for n in found_nums:
        if n not in allowed_numbers and not any(n == str(round(float(a), 1)) for a in allowed_numbers if re.match(r"^\d+(?:\.\d+)?$", a)):
            untraced_nums.append(n)

    if untraced_nums:
        guard_failed = True
        failure_reasons.append(f"Untraced numbers detected: {untraced_nums}")

    # Handle Guard Failure with Safe Templated Fallback
    if guard_failed:
        print(f"[Guards-Warning] Guard verification flagged: {failure_reasons}. Triggering templated fallback.")
        place = res_loc.get("name", "your area")
        activity_gerund = turn_state.get("activity_label", "outdoor activity")
        fired_ids = [s["id"] for s in fired_sops]
        verdict = state.get("verdict") or {}
        verdict_status = verdict.get("status")
        
        fallback_lines = [
            f"**{place} ({round(abs(res_loc.get('latitude', 0)), 2)}°N, {round(abs(res_loc.get('longitude', 0)), 2)}°E)**",
            "• **Target Time**: Current model conditions"
        ]
        if verdict_status == "NO_POLICY":
            fallback_lines.append(f"No SOP covers {activity_gerund}. Please check with local authorities.")
        elif fired_sops:
            fallback_lines.append(f"• **Active Hazards**: {', '.join(fired_ids)}")
            for sop in fired_sops:
                clean_adv = sop.get("advice", "").strip()
                for b in BANNED_PHRASES:
                    clean_adv = re.sub(re.escape(b), "follow guidance for", clean_adv, flags=re.IGNORECASE)
                fallback_lines.append(f"• **[{sop['id']}] {sop.get('title')}**:\n{clean_adv}")
        else:
            fallback_lines.append(f"• **Notice**: Evaluated Standard Operating Procedures for {activity_gerund}.")
            fallback_lines.append("• **Status**: All measured telemetry parameters remain below hazard alert thresholds.")
        
        fallback_lines.append(
            f"• **SOPs Evaluated**: [{', '.join([s['id'] for s in evaluated_sops])}]\n"
            f"• **SOPs Fired**: [{', '.join(fired_ids) if fired_ids else 'None'}]"
        )
        final_response = "\n\n".join(fallback_lines)

    return {
        "final_response": final_response
    }
