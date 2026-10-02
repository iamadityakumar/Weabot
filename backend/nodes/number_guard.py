import re
from typing import Dict, Any, Set, List, Tuple
from backend.agent_state import AgentState

def validate_and_guard_numbers(state: AgentState) -> Dict[str, Any]:
    """
    Post-render runtime number guard.
    Extracts every integer and floating-point number from the generated final_response
    and validates it against:
    1. Raw Open-Meteo telemetry numbers (current, target hourly, daily).
    2. Derived arithmetical conversions (km/h -> m/s, km/h -> mph, °C -> °F, roundings).
    3. SOP-literal numbers from conditions and advice text of matched SOPs.
    4. User's own quoted numbers from the input prompt.
    5. Standard structural formatting numbers (timestamps, percentages, safe intervals).

    If any untraced or hallucinated number is detected, replaces the response
    with a deterministic templated fallback containing only verified facts.
    """
    final_response = state.get("final_response", "")
    weather_data = state.get("effective_weather") or state.get("weather_data") or {}
    matched_sops = state.get("matched_sops") or []
    messages = state.get("messages") or []
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")

    # Build allowed numbers whitelist
    allowed_numbers: Set[str] = set()

    # 1. Raw telemetry numbers
    curr = weather_data.get("current", {})
    if isinstance(curr, dict):
        for k, v in curr.items():
            if isinstance(v, (int, float)):
                allowed_numbers.add(str(v))
                allowed_numbers.add(str(int(v)))
                allowed_numbers.add(str(round(float(v), 1)))
                allowed_numbers.add(str(round(float(v), 2)))

    # Derived unit conversions for wind and gusts
    wind = curr.get("wind_speed_10m")
    if wind is not None and isinstance(wind, (int, float)):
        w = float(wind)
        ms = w * 1000 / 3600
        mph = w / 1.60934
        for val in [ms, mph]:
            allowed_numbers.update([str(round(val, 1)), str(round(val, 2)), str(int(round(val)))])

    gusts = curr.get("wind_gusts_10m")
    if gusts is not None and isinstance(gusts, (int, float)):
        g = float(gusts)
        ms = g * 1000 / 3600
        mph = g / 1.60934
        for val in [ms, mph]:
            allowed_numbers.update([str(round(val, 1)), str(round(val, 2)), str(int(round(val)))])

    temp = curr.get("temperature_2m")
    if temp is not None and isinstance(temp, (int, float)):
        t = float(temp)
        f_val = t * 9 / 5 + 32
        allowed_numbers.update([str(round(f_val, 1)), str(int(round(f_val)))])

    # SOP-literal numbers
    for sop in matched_sops:
        advice_text = sop.get("advice", "")
        for n in re.findall(r"\b\d+(?:\.\d+)?\b", advice_text):
            allowed_numbers.add(n)
        for cond in sop.get("conditions", []):
            for n in re.findall(r"\b\d+(?:\.\d+)?\b", str(cond)):
                allowed_numbers.add(n)

    # Numbers from unverified SOPs and citations
    unverified_sops = state.get("unverified_sops") or []
    for u in unverified_sops:
        sop_id = u.get("sop_id", "")
        for n in re.findall(r"\b\d+\b", sop_id):
            allowed_numbers.add(n)
            allowed_numbers.add(str(int(n)))

    for cid in state.get("sop_citations") or []:
        for n in re.findall(r"\b\d+\b", cid):
            allowed_numbers.add(n)
            allowed_numbers.add(str(int(n)))

    # 3. User-quoted numbers
    for n in re.findall(r"\b\d+(?:\.\d+)?\b", user_query):
        allowed_numbers.add(n)

    # 4. Target hours, timestamps, standard safe numbers
    target_hour = weather_data.get("eval_target_hour", "")
    if target_hour:
        for n in re.findall(r"\b\d+\b", target_hour):
            allowed_numbers.add(n)
    eval_time = weather_data.get("eval_target_time", "")
    if eval_time:
        for n in re.findall(r"\b\d+\b", eval_time):
            allowed_numbers.add(n)

    # Standard safe numerals (single digits, percentages, common time constants)
    allowed_numbers.update([
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "12", "13", "14", "15", "18", "20", "24", "30", "40", "45", "48",
        "50", "60", "70", "80", "90", "100", "400", "1000", "2026", "2024"
    ])

    # Extract all numbers from generated text
    found_nums = re.findall(r"\b\d+(?:\.\d+)?\b", final_response)
    unauthorized = []
    for n in found_nums:
        if n in allowed_numbers:
            continue
        # Fuzzy float check
        try:
            fn = float(n)
            is_close = any(abs(fn - float(an)) < 0.05 for an in allowed_numbers if an.replace('.', '', 1).isdigit())
            if not is_close:
                unauthorized.append(n)
        except ValueError:
            unauthorized.append(n)

    if unauthorized:
        print(f"[NumberGuard] [ALERT] Unauthorized number(s) detected: {unauthorized}. Substituting deterministic fallback.")
        safe_fallback = _generate_safe_fallback(state)
        return {
            "final_response": safe_fallback,
            "number_guard_triggered": True,
            "unauthorized_numbers": unauthorized
        }

    return {
        "final_response": final_response,
        "number_guard_triggered": False
    }

def _generate_safe_fallback(state: AgentState) -> str:
    """Generate deterministic, 100% verified fallback when number guard triggers."""
    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity", "outdoor activity")
    session_facts = dict(state.get("session_facts") or {})
    location = session_facts.get("location_display") or session_facts.get("location_name") or "your area"
    weather = state.get("effective_weather") or state.get("weather_data") or {}
    curr = weather.get("current", {})
    matched_sops = state.get("matched_sops") or []
    unverified = state.get("unverified_sops") or []

    # If telemetry is incomplete, return honest unverified telemetry notice
    if unverified:
        sop_lines = []
        for u in unverified:
            missing_str = ", ".join(f"`{f}`" for f in u["missing_fields"])
            sop_lines.append(f"• **[{u['sop_id']}] {u['title']}** (requires {missing_str} telemetry)")
        return (
            f"⚠️ **Safety Telemetry Incomplete for {location}**:\n\n"
            f"We have active Standard Operating Procedures covering **{activity}**, but the following safety policy could not be evaluated "
            f"because essential live weather metrics are currently unavailable from the weather data service:\n\n"
            f"{chr(10).join(sop_lines)}\n\n"
            "Because I am looking out for your safety as Weabot, our policy strictly prohibits assuming unverified conditions are safe or guessing "
            "missing values. Please check local conditions or direct observation reports before heading outside."
        )

    temp = curr.get("temperature_2m")
    wind = curr.get("wind_speed_10m")
    precip = curr.get("precipitation")

    temp_str = f"{temp}°C" if temp is not None else "unavailable"
    wind_str = f"{wind} km/h" if wind is not None else "unavailable"
    precip_str = f"{precip} mm" if precip is not None else "unavailable"

    if matched_sops:
        sop_bullets = []
        for s in matched_sops:
            sop_bullets.append(f"• **[{s.get('id')}] {s.get('title')}** ({s.get('severity', '').upper()}):\n{s.get('advice')}")
        return (
            f"**Verified Safety Guidance for {activity.title()} in {location}**:\n\n"
            f"*Model-based current conditions in {location}: Temperature {temp_str}, Wind Speed {wind_str}, Precipitation {precip_str}.*\n\n"
            f"{chr(10).join(sop_bullets)}\n\n"
            "*(Notice: Response verified by runtime number guard to guarantee 100% telemetry fidelity.)*"
        )
    else:
        return (
            f"Model-based current conditions in **{location}** were evaluated against active Standard Operating Procedures for **{activity}**, "
            "and no hazard alert thresholds were exceeded.\n\n"
            f"• **Model-based current conditions**: Temperature ~{temp_str}, wind {wind_str}, precipitation {precip_str}.\n\n"
            "*(Notice: Weabot does not issue general safety clearances. Conditions may change.)*"
        )
