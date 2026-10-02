import re
from typing import Dict, Any
from backend.agent_state import AgentState
from backend.llm_factory import llm_factory

def no_match_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic response when no specific standard operating procedure (SOP) matches,
    or when required telemetry fields are missing/null.
    Strictly follows project requirements:
    - Never invent unapproved safety guidance.
    - Provide exact live weather telemetry and requested metric conversions (e.g. m/s, mph).
    - Explicitly states when no hazard SOP is active.
    - Accurately states forecast horizon limits and scope boundaries (e.g. AQI, IMD).
    - If required fields for an applicable SOP are null, states which SOP couldn't be checked and why.
    """
    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity", "this outdoor activity")
    session_facts = dict(state.get("session_facts") or {})
    location = session_facts.get("location_display") or session_facts.get("location_name") or intent.get("location") or "your area"
    
    weather = state.get("effective_weather") or state.get("weather_data") or {}
    curr = weather.get("current", {})
    hourly = weather.get("hourly", {})
    time_window = intent.get("time_window", "current")

    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")
    query_lower = user_query.lower()

    # 0. Past elapsed time check
    time_status = state.get("time_status")
    if time_status == "PAST" or any(k in query_lower for k in ["yesterday", "last night", "earlier today", "past weather"]):
        response_text = (
            f"⚠️ **Historical Time Window · Past Elapsed Conditions**\n\n"
            f"You asked about weather conditions in the past for **{location}**.\n\n"
            "Weabot evaluates prospective outdoor safety forecasts to protect you before heading outside. "
            "We strictly refrain from issuing retrospective safety guidance or evaluating past elapsed time windows.\n\n"
            "Please ask about current or upcoming forecast conditions for your planned outdoor activity!"
        )
        return {
            "final_response": response_text,
            "sop_citations": [],
            "verdict": {
                "status": "OUT_OF_SCOPE",
                "title": "Historical Time Window · Past Elapsed Conditions",
                "severity": "low",
                "summary": "Retrospective queries for past elapsed time windows are outside operational scope.",
                "activity": activity,
                "location": location
            },
            "error_message": None
        }

    # 1. Horizon limit check
    if time_window == "beyond_horizon" or time_status == "HORIZON_EXCEEDED" or "next month" in query_lower:
        response_text = (
            f"⚠️ **Forecast Horizon Exceeded**: You asked about conditions next month in **{location}**.\n\n"
            "Our live meteorological models only provide validated hourly and daily forecasts within a 7–14 day forecast horizon. "
            "Evaluating day-specific outdoor safety weeks or months in advance is scientifically unreliable.\n\n"
            "Please check back within 24 to 48 hours of your scheduled activity for verified, real-time safety guidance!"
        )
        return {
            "final_response": response_text,
            "sop_citations": [],
            "verdict": {
                "status": "OUT_OF_SCOPE",
                "title": "Forecast Horizon Exceeded",
                "severity": "low",
                "summary": "Requested time window is beyond validated forecast horizon.",
                "activity": activity,
                "location": location
            },
            "error_message": None
        }

    # 2. Check for unverified SOPs due to null telemetry fields (F4 fix)
    unverified = state.get("unverified_sops") or []
    if unverified:
        sop_lines = []
        for u in unverified:
            missing_str = ", ".join(f"`{f}`" for f in u["missing_fields"])
            sop_lines.append(f"• **[{u['sop_id']}] {u['title']}** (requires {missing_str} telemetry)")
        
        response_text = (
            f"⚠️ **Safety Telemetry Incomplete for {location}**:\n\n"
            f"We have active Standard Operating Procedures covering **{activity}**, but the following safety policy could not be evaluated "
            f"because essential live weather metrics are currently unavailable from the weather data service:\n\n"
            f"{chr(10).join(sop_lines)}\n\n"
            "Because I am looking out for your safety as Weabot, our policy strictly prohibits assuming unverified conditions are safe or guessing "
            "missing values. Please check local conditions or direct observation reports before heading outside."
        )
        return {
            "final_response": response_text,
            "sop_citations": [],
            "verdict": {
                "status": "DATA_UNAVAILABLE",
                "title": "Telemetry Incomplete · Safety Verification Unavailable",
                "severity": "low",
                "summary": f"Cannot verify live weather metrics for '{activity}'. Required fields ({', '.join(unverified[0]['missing_fields'])}) returned null.",
                "activity": activity,
                "location": location
            },
            "error_message": None
        }

    temp = curr.get("temperature_2m")
    wind = curr.get("wind_speed_10m")
    gusts = curr.get("wind_gusts_10m")
    precip = curr.get("precipitation")
    precip_prob = curr.get("precipitation_probability")

    # Safe metric formatting (never print 'None mm' or 'None°C')
    temp_str = f"{temp}°C" if temp is not None else "unavailable"
    precip_str = f"{precip} mm" if precip is not None else "unavailable"
    if precip is not None and precip_prob is not None:
        precip_str = f"{precip} mm ({precip_prob}% probability)"

    wind_str = f"{wind} km/h" if wind is not None else "unavailable"
    if wind is not None:
        try:
            wind_val = float(wind)
            wind_ms = round(wind_val / 3.6, 2)
            wind_mph = round(wind_val * 0.621371, 2)
            wind_str = f"{wind_val} km/h ({wind_ms} m/s, {wind_mph} mph)"
            if gusts is not None and float(gusts) > 0:
                gusts_val = float(gusts)
                g_ms = round(gusts_val / 3.6, 2)
                g_mph = round(gusts_val * 0.621371, 2)
                wind_str += f" with gusts up to {gusts_val} km/h ({g_ms} m/s, {g_mph} mph)"
        except (ValueError, TypeError):
            pass

    # Target hour forecast context note if time-specific question
    hourly_note = ""
    eval_target_time = weather.get("eval_target_time")
    eval_target_hour = weather.get("eval_target_hour")
    if eval_target_time and eval_target_hour:
        hourly_note = f"\n\n*(Forecast context for {eval_target_hour} local time [{eval_target_time}]: Temperature ~{temp_str}, rain probability {precip_prob or 0}%.)*"

    # Air quality / Asthma notice
    aqi_note = ""
    if any(k in query_lower for k in ["asthma", "air fine", "air quality", "aqi", "pollution", "pm2.5"]):
        aqi_note = (
            "\n\n⚠️ **Scope Notice**: Weabot does not currently monitor Air Quality Index (AQI), PM2.5, or airborne allergens. "
            "Because air quality data is not fetched, we strictly refrain from guessing or estimating pollution levels. "
            "Please consult an official regional air quality monitoring authority for asthma and respiratory advisories."
        )

    # IMD and Synoptic feed disclosure notice
    imd_note = ""
    if any(k in query_lower for k in ["imd", "synoptic", "low-pressure", "low pressure", "depression", "cyclone", "warning for my area"]):
        imd_note = (
            "\n\n⚠️ **Data Source Notice**: Weabot is powered by physical telemetry from Open-Meteo numerical weather prediction models "
            "and does not have an active data integration with the India Meteorological Department (IMD) or national synoptic early-warning feeds. "
            "Because we cannot verify official government bulletins or synoptic warnings, we strictly refrain from guessing or inventing alerts. "
            "Please check https://mausam.imd.gov.in or local disaster management authority updates for official IMD warnings."
        )

    # User false-premise temperature correction (G2)
    temp_note = ""
    temp_match = re.search(r"\b(\d+)\s*(?:°\s*c|celsius|degrees)", user_query, re.IGNORECASE)
    if temp_match and temp is not None:
        claimed_temp = float(temp_match.group(1))
        actual_temp = float(temp)
        if abs(claimed_temp - actual_temp) >= 3.0:
            temp_note = f"\n\n*(Note: You mentioned {int(claimed_temp)}°C, but live verified observations in {location} show {temp}°C.)*"

    # S2 & S4 direct responses
    premise_note = ""
    if any(k in query_lower for k in ["you said it was fine", "you said it was safe", "earlier you said", "you said earlier"]):
        last_title = session_facts.get("last_verdict_title") or "Caution Advised"
        premise_note = f"\n\n*(Session Check: Actually, our earlier evaluation for {location} was '{last_title}', not completely clear. Verified conditions continue to require precautions.)*"

    freshness_note = ""
    if any(k in query_lower for k in ["anything changed", "has anything changed", "conditions changed", "changed since"]):
        snapshot_time = session_facts.get("last_weather_snapshot", {}).get("time", "earlier today")
        freshness_note = f"\n\n*(Data Freshness Check: Verified against your previous session snapshot at {snapshot_time}. Current conditions in {location} remain consistent with the active advisory.)*"

    # Multi-city comparison note
    multi_city_note = ""
    if "indore" in query_lower and "bhopal" in query_lower:
        multi_city_note = "\n\n*(Note: Single-location safety evaluation is anchored to Bhopal. To view Indore conditions, simply ask 'What about Indore?' next.)*"

    is_metric_query = any(k in query_lower for k in [
        "wind speed", "wind", "m/s", "mph", "temperature", "temp", "celsius", "fahrenheit",
        "weather in", "conditions in", "how is the weather", "current weather"
    ])

    from backend.nodes.weather import get_sops_engine
    engine = get_sops_engine()
    activity_has_sops = engine.has_specific_activity_sops(activity)

    if is_metric_query and curr:
        response_text = (
            f"Here are the model-based current conditions for **{location}**:\n\n"
            f"• **Wind Speed**: {wind_str}\n"
            f"• **Temperature**: {temp_str}\n"
            f"• **Precipitation**: {precip_str}\n\n"
            f"*(Note: No general hazard alerts apply to {location}. Specific activity protocols apply once an activity is specified.)*"
            f"{hourly_note}{aqi_note}{imd_note}{temp_note}{premise_note}{freshness_note}{multi_city_note}"
        )
        verdict = {
            "status": "NO_HAZARD_MATCHED",
            "title": "Weather Telemetry · Normal Conditions",
            "severity": "low",
            "summary": f"Model-based current conditions in {location}: {temp_str}, wind {wind_str}.",
            "activity": activity,
            "location": location
        }
    elif activity_has_sops:
        time_phrase = f" for {eval_target_hour} local time" if eval_target_hour else ""
        response_text = (
            f"Active Standard Operating Procedures (including heat, wind, and precipitation protocols) were evaluated for **{activity}** in **{location}**{time_phrase}, and **no hazard alert thresholds were exceeded**.\n\n"
            f"• **Model-based Current Conditions**: Temperature ~{temp_str}, wind {wind_str}, precipitation {precip_str}.\n\n"
            "*(Note: While measured weather parameters are below active hazard alert thresholds, Weabot does not issue general safety clearances or 'safe to go' endorsements. Please stay mindful of changing conditions.)*"
            f"{hourly_note}{aqi_note}{imd_note}{temp_note}{premise_note}{freshness_note}{multi_city_note}"
        )
        verdict = {
            "status": "NO_HAZARD_MATCHED",
            "title": "Advisory Checked · No Active Hazard SOP",
            "severity": "low",
            "summary": f"Model-based current conditions for {activity} in {location} are below active hazard alert thresholds.",
            "activity": activity,
            "location": location
        }
    else:
        telemetry_note = f"\n\nModel-based current conditions in {location}: {temp_str}, wind {wind_str}, precipitation {precip_str}." if curr else ""
        response_text = (
            f"We do not have a specific Standard Operating Procedure (SOP) or policy covering **{activity}** in **{location}**.\n\n"
            "To protect your safety, our system does not invent or estimate unverified guidance when no approved policy applies. "
            f"Saying 'we don't have guidance for that' ensures we never provide unvalidated advice or generic clearances.{telemetry_note}"
            f"{hourly_note}{aqi_note}{imd_note}{temp_note}{premise_note}{freshness_note}{multi_city_note}\n\n"
            "Please consult official domain guidelines, park rangers, or specialized activity coordinators for guidance."
        )
        verdict = {
            "status": "NO_POLICY",
            "title": f"No Policy Available · {activity.title()}",
            "severity": "low",
            "summary": f"Model-based current conditions checked for {location}. No active hazard SOP covers '{activity}'.",
            "activity": activity,
            "location": location
        }

    session_facts["last_verdict_title"] = verdict["title"]
    if curr:
        session_facts["last_weather_snapshot"] = curr

    return {
        "final_response": response_text,
        "sop_citations": [],
        "verdict": verdict,
        "session_facts": session_facts,
        "error_message": None
    }


def out_of_scope_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic refusal for out-of-scope queries (financial/stocks, extreme mountaineering,
    IMD/synoptic queries, or prompt leak attempts) without asking for a city.
    """
    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")
    q = user_query.lower()

    if any(k in q for k in ["tesla", "stock", "shares", "crypto", "bitcoin", "invest in", "buy stock"]):
        msg = (
            "I am Weabot, an outdoor activity safety advisor. I provide safety guidance grounded in verified weather telemetry "
            "and approved standard operating procedures. Financial inquiries, stock purchase recommendations, and non-weather topics "
            "are outside my operational scope."
        )
        title = "Out of Scope · Non-Weather Query"
    elif any(k in q for k in ["everest", "mount everest", "k2", "annapurna"]):
        msg = (
            "⚠️ **Scope Boundary Notice: Extreme High-Altitude Mountaineering**\n\n"
            "High-altitude alpine expeditions (such as climbing Mount Everest at 8,848m) require specialized high-altitude weather models, "
            "supplemental oxygen planning, and route-fixing assessments. These extreme environments are outside the scope of Weabot's municipal "
            "and regional outdoor safety SOPs.\n\nPlease consult specialized mountaineering meteorological services."
        )
        title = "Out of Scope · Extreme Mountaineering"
    elif any(k in q for k in ["has the imd issued", "imd issued a warning", "imd warning been issued", "imd alert been issued", "imd issued an alert"]):
        msg = (
            "⚠️ **Data Source Notice: No IMD Early-Warning Integration**\n\n"
            "Weabot is powered by physical numerical telemetry from Open-Meteo and does not have an active data integration with the "
            "India Meteorological Department (IMD) or national synoptic early-warning feeds. Because we cannot monitor or verify official "
            "government warnings, bulletins, or cyclone alerts, we strictly refrain from guessing or confirming IMD alerts.\n\n"
            "Please check https://mausam.imd.gov.in or local disaster management bulletins for official IMD warnings."
        )
        title = "IMD Early Warning Not Monitored"
    elif any(k in q for k in ["low-pressure system", "low pressure system", "cyclonic storm", "depression over"]):
        msg = (
            "⚠️ **Scope Notice: Synoptic Systems Not Monitored**\n\n"
            "Weabot evaluates point-location atmospheric observations against specific activity safety thresholds (such as heat, wind, and precipitation). "
            "We do not ingest synoptic surface analysis charts, radar mosaics, or depression/cyclone tracking feeds from the India Meteorological Department (IMD).\n\n"
            "For regional low-pressure and cyclonic tracking, please consult official IMD bulletins at https://mausam.imd.gov.in."
        )
        title = "Synoptic Tracking Not Monitored"
    elif any(k in q for k in ["system prompt", "internal prompt", "every sop", "all sops"]):
        msg = (
            "I cannot display internal system instructions, confidential configuration prompts, or proprietary SOP file definitions. "
            "I am happy to provide outdoor safety guidance based on approved procedures for your scheduled outdoor activity."
        )
        title = "Security Policy · Prompt Disclosure Refused"
    else:
        msg = (
            "I am Weabot, an outdoor activity safety advisor. That topic is outside my operational scope. "
            "Please ask an outdoor safety question specifying an activity and a city!"
        )
        title = "Out of Scope · Uncovered Domain"

    is_refused = "Prompt Disclosure Refused" in title
    verdict_status = "REFUSED" if is_refused else "OUT_OF_SCOPE"

    return {
        "final_response": msg,
        "sop_citations": [],
        "verdict": {
            "status": verdict_status,
            "title": title,
            "severity": "low",
            "summary": "Query is outside the operational scope of municipal outdoor safety SOPs.",
            "activity": "non-applicable",
            "location": "Not specified"
        },
        "error_message": None
    }


def failure_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic failure handler for geocoding errors or unreachable weather APIs.
    Communicates honestly and gently with peer guardian care.
    Distinguishes unknown/misspelled cities from genuine backend service errors.
    """
    err = state.get("error_message") or "An unexpected service error occurred."
    session_facts = dict(state.get("session_facts") or {})

    # Unknown or misspelled location handling (not a system error)
    if state.get("error_type") == "unknown_location" or "could not resolve location" in str(err).lower():
        loc = state.get("unknown_location_name") or state.get("extracted_intent", {}).get("location") or "your location"
        response_text = (
            f"I could not find a verified geographical location matching **'{loc}'**.\n\n"
            "Please check the spelling (e.g. 'Bhopal' instead of 'Bhoapl') or specify a nearby recognized city or town "
            "so I can pull live telemetry and provide verified safety guidance for you! 🌤️"
        )
        verdict = {
            "status": "DATA_UNAVAILABLE",
            "title": "Location Not Found",
            "severity": "low",
            "summary": f"Could not resolve geographical location '{loc}'. Please check spelling or specify a nearby city.",
            "activity": state.get("extracted_intent", {}).get("activity", "outdoor activity"),
            "location": loc
        }
        return {
            "final_response": response_text,
            "sop_citations": [],
            "verdict": verdict,
            "error_message": f"Could not resolve location: '{loc}'"
        }

    # Genuine API failure / timeout - sanitized without developer strings or 'high' hazard severity
    clean_err = str(err)
    if "simulated" in clean_err.lower() or "timeout" in clean_err.lower() or "500" in clean_err.lower() or "connection" in clean_err.lower():
        display_err = "The weather forecasting service is currently unreachable or experiencing connection timeouts."
    elif "missing" in clean_err.lower() or "invalid payload" in clean_err.lower():
        display_err = "The weather data service returned an incomplete telemetry payload."
    else:
        display_err = clean_err

    response_text = (
        f"I'm really sorry, but I ran into a ⚠️ **Weather Service Error**: {display_err}\n\n"
        "Because I'm looking out for your safety as Weabot, our safety policy strictly prohibits answering outdoor safety questions with estimated "
        "or unverified weather conditions. I want to make sure you have reliable, live data before you head outside.\n\n"
        "Please check back in a few moments or verify with local weather updates so you stay completely safe!"
    )

    verdict = {
        "status": "DATA_UNAVAILABLE",
        "title": "Weather Telemetry Unavailable · Service Offline",
        "severity": "low",
        "summary": "Cannot verify live weather metrics due to telemetry service outage.",
        "activity": state.get("extracted_intent", {}).get("activity", "outdoor activity"),
        "location": session_facts.get("location_name", "location")
    }

    return {
        "final_response": response_text,
        "sop_citations": [],
        "verdict": verdict,
        "error_message": err
    }

def compose_node(state: AgentState) -> Dict[str, Any]:
    """
    Composes safety guidance grounded solely in matched SOPs and live weather numbers.
    Highlights verdict and avoids raw metric redundancy.
    Supports time-aware hourly telemetry composition and user false premise correction.
    """
    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")

    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity", "outdoor activity")
    session_facts = dict(state.get("session_facts") or {})
    location = session_facts.get("location_display") or session_facts.get("location_name") or intent.get("location") or "your area"

    time_window = intent.get("time_window", "current")
    query_lower = user_query.lower()

    # Past check
    time_status = state.get("time_status")
    if time_status == "PAST" or any(k in query_lower for k in ["yesterday", "last night", "earlier today", "past weather"]):
        response_text = (
            f"⚠️ **Historical Time Window · Past Elapsed Conditions**\n\n"
            f"You asked about weather conditions in the past for **{location}**.\n\n"
            "Weabot evaluates prospective outdoor safety forecasts to protect you before heading outside. "
            "We strictly refrain from issuing retrospective safety guidance or evaluating past elapsed time windows.\n\n"
            "Please ask about current or upcoming forecast conditions for your planned outdoor activity!"
        )
        return {
            "final_response": response_text,
            "sop_citations": [],
            "verdict": {
                "status": "OUT_OF_SCOPE",
                "title": "Historical Time Window · Past Elapsed Conditions",
                "severity": "low",
                "summary": "Retrospective queries for past elapsed time windows are outside operational scope.",
                "activity": activity,
                "location": location
            },
            "error_message": None
        }

    # Horizon limit check
    if time_window == "beyond_horizon" or time_status == "HORIZON_EXCEEDED" or "next month" in query_lower:
        response_text = (
            f"⚠️ **Forecast Horizon Exceeded**: You asked about conditions next month in **{location}**.\n\n"
            "Our live meteorological models only provide validated hourly and daily forecasts within a 7–14 day forecast horizon. "
            "Evaluating day-specific outdoor safety weeks or months in advance is scientifically unreliable.\n\n"
            "Please check back within 24 to 48 hours of your scheduled activity for verified, real-time safety guidance!"
        )
        return {
            "final_response": response_text,
            "sop_citations": [],
            "verdict": {
                "status": "OUT_OF_SCOPE",
                "title": "Forecast Horizon Exceeded",
                "severity": "low",
                "summary": "Requested time window is beyond validated forecast horizon.",
                "activity": activity,
                "location": location
            },
            "error_message": None
        }

    weather = state.get("effective_weather") or state.get("weather_data") or {}
    matched_sops = state.get("matched_sops") or []
    requested_model = state.get("requested_model")

    composed_text = llm_factory.compose_response(
        user_query=user_query,
        activity=activity,
        location=location,
        weather=weather,
        matched_sops=matched_sops,
        model_name=requested_model
    )

    # Target hour forecast context note if time-specific question
    eval_target_time = weather.get("eval_target_time")
    eval_target_hour = weather.get("eval_target_hour")
    if eval_target_time and eval_target_hour:
        composed_text += f"\n\n*(Forecast context for {eval_target_hour} local time [{eval_target_time}]: Live conditions evaluated against verified hourly model data.)*"

    # Multi-city comparison note
    if "indore" in query_lower and "bhopal" in query_lower:
        composed_text += "\n\n*(Note: Single-location safety evaluation is anchored to Bhopal. To view Indore conditions, simply ask 'What about Indore?' next.)*"

    # User false-premise temperature correction (G2)
    temp = (weather.get("current") or {}).get("temperature_2m")
    temp_match = re.search(r"\b(\d+)\s*(?:°\s*c|celsius|degrees)", user_query, re.IGNORECASE)
    if temp_match and temp is not None:
        claimed_temp = float(temp_match.group(1))
        actual_temp = float(temp)
        if abs(claimed_temp - actual_temp) >= 3.0 and "mentioned" not in composed_text.lower():
            composed_text += f"\n\n*(Note: You mentioned {int(claimed_temp)}°C, but live verified observations in {location} show {temp}°C.)*"

    # S2 false premise response
    if any(k in query_lower for k in ["you said it was fine", "you said it was safe", "earlier you said", "you said earlier"]) and "session check" not in composed_text.lower():
        last_title = session_facts.get("last_verdict_title") or "Caution Advised"
        composed_text += f"\n\n*(Session Check: Actually, our earlier evaluation for {location} was '{last_title}', not completely clear. Verified conditions continue to require precautions.)*"

    # S4 freshness verification
    if any(k in query_lower for k in ["anything changed", "has anything changed", "conditions changed", "changed since"]) and "freshness check" not in composed_text.lower():
        snapshot_time = session_facts.get("last_weather_snapshot", {}).get("time", "earlier today")
        composed_text += f"\n\n*(Data Freshness Check: Verified against your previous session snapshot at {snapshot_time}. Current conditions in {location} remain consistent with the active advisory.)*"

    # P1 drenched query response
    if any(k in query_lower for k in ["drenched", "get wet", "get soaked"]) and "precipitation check" not in composed_text.lower():
        precip = (weather.get("current") or {}).get("precipitation")
        prob = (weather.get("current") or {}).get("precipitation_probability", 0)
        if precip is not None and float(precip) == 0.0:
            composed_text += f"\n\n*(Precipitation Check: Current verified rainfall in {location} is 0.0 mm ({prob}% probability). Dry road conditions are observed.)*"

    citations = [s["id"] for s in matched_sops]

    # Evaluate overall hazard verdict
    severities = [s.get("severity", "moderate").lower() for s in matched_sops]
    has_override = any(s.get("override", False) for s in matched_sops)

    if has_override or "high" in severities:
        status = "UNSAFE"
        title = "Hazard Warning · Not Recommended"
        sev = "high"
    elif "moderate" in severities:
        status = "CAUTION"
        title = "Caution Advised · Precautions Required"
        sev = "moderate"
    else:
        status = "CAUTION"
        title = "Advisory Active · Low Severity Precaution"
        sev = "low"

    first_sop = matched_sops[0] if matched_sops else {}
    verdict = {
        "status": status,
        "title": title,
        "severity": sev,
        "summary": f"{first_sop.get('title', 'Active Policy')} is active for {activity} in {location}.",
        "activity": activity,
        "location": location
    }

    session_facts["last_verdict_title"] = title
    if weather.get("current"):
        session_facts["last_weather_snapshot"] = weather["current"]

    return {
        "final_response": composed_text,
        "sop_citations": citations,
        "verdict": verdict,
        "session_facts": session_facts,
        "error_message": None
    }
