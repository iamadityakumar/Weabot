import re
from typing import Dict, Any, Optional
from backend.agent_state import AgentState, SafetyStatus
from backend.nodes.location import get_weather_client
from backend.weather_client import GeocodingError

async def resolve_location_node(state: AgentState) -> Dict[str, Any]:
    """
    WP1 & WP2 Location Resolver:
    - Resolves place name via Open-Meteo Geocoding.
    - Strict carry-over rule: carry location ONLY for follow-up phrasing when no location is given.
    - A failed geocode must NEVER write to SessionState!
    - Handles coordinates & open-ocean input with a plain message.
    - Handles Devanagari with honest script support message.
    - On failure: routes to location_fail.
    """
    turn_state = dict(state.get("turn_state") or {})
    session_state = state.get("session_state") or {}
    last_good = session_state.get("last_good_location")
    user_query = turn_state.get("raw_query", "")
    query_lower = user_query.lower()
    raw_loc = turn_state.get("raw_location")
    is_followup = turn_state.get("is_followup", False)

    # 1. Devanagari check
    if re.search(r"[\u0900-\u097F]", user_query):
        turn_state["error_type"] = "location_fail"
        turn_state["error_message"] = (
            "Weabot currently supports queries in English and Latin transliteration (e.g. 'Bhopal'). "
            "Non-Latin Devanagari script is not currently parsed. "
            "Please specify your location in Latin characters so I can check live weather safety for you."
        )
        return {"turn_state": turn_state}

    # 2. Coordinates / open-ocean check (#27)
    # Check for direct decimal coordinates e.g. "23.25, 77.41" or "middle of the pacific"
    coord_match = re.search(r"([-+]?[1-8]?\d(?:\.\d+)?|90(?:\.0+)?),\s*([-+]?(?:180(?:\.0+)?|(?:1[0-7]\d|\d{1,2})(?:\.\d+)?))", user_query)
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        turn_state["error_type"] = "location_fail"
        turn_state["error_message"] = (
            f"Coordinates ({lat:.2f}°N, {lon:.2f}°E) resolved. "
            "No land-based municipal jurisdiction or outdoor activity safety policy covers open water or remote coordinates. "
            "Please consult maritime or local emergency authorities."
        )
        return {"turn_state": turn_state}

    if any(k in query_lower for k in ["middle of the pacific", "pacific ocean", "open ocean", "middle of the atlantic"]):
        turn_state["error_type"] = "location_fail"
        turn_state["error_message"] = (
            "Ocean coordinates resolved. No land-based municipal jurisdiction or outdoor activity safety policy covers open water. "
            "Please consult maritime navigation authorities."
        )
        return {"turn_state": turn_state}

    # 3. Handle location-less queries: "What's it like here?" / missing location (#27)
    if any(k in query_lower for k in ["what's it like here", "what is it like here", "weather here"]):
        if not last_good:
            turn_state["error_type"] = "location_fail"
            turn_state["error_message"] = "Could you tell me which city or town you'd like the weather safety check for?"
            return {"turn_state": turn_state}

    # 4. Check if location candidate is provided
    # Extract candidate from raw_location or prepositional phrase in user query
    cand = raw_loc
    if not cand:
        # Search preposition phrases: in <City>, near <City>, at <City>
        m_prep = re.search(r"\b(?:in|around|near|at)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", user_query, re.IGNORECASE)
        if m_prep:
            cand = m_prep.group(1).strip()
            # Trim trailing temporal tokens
            cand = re.sub(r"\b(today|tomorrow|yesterday|now|right now|this|next)\b.*$", "", cand, flags=re.IGNORECASE).strip()

    # 5. Geocode candidate or apply follow-up carry-over
    weather_client = get_weather_client()

    if cand and cand.lower() not in ("here", "there", "everywhere"):
        try:
            geo = await weather_client.geocode(cand)
            if geo and geo.get("latitude") is not None:
                name = geo["name"]
                admin1 = geo.get("admin1")
                country = geo.get("country")
                display = f"{name} ({admin1}, {country})" if admin1 and country else (f"{name} ({admin1})" if admin1 else name)
                
                resolved = {
                    "name": name,
                    "display": display,
                    "latitude": geo["latitude"],
                    "longitude": geo["longitude"],
                    "timezone": geo.get("timezone", "UTC"),
                    "admin1": admin1,
                    "country": country
                }
                turn_state["resolved_location"] = resolved
                # Note: SessionState is updated only on successful flow in log_decision!
                return {"turn_state": turn_state}
        except GeocodingError:
            # Geocoding failed!
            # WP1 Non-Negotiable: "A failed geocode must never write to SessionState."
            turn_state["error_type"] = "location_fail"
            turn_state["error_message"] = f"Could not resolve location: '{cand}'. Please check spelling or enter a recognized city or town."
            return {"turn_state": turn_state}

    # No location given in query. Check if carry-over applies
    if is_followup and last_good:
        turn_state["resolved_location"] = dict(last_good)
        return {"turn_state": turn_state}

    # Missing location entirely
    turn_state["error_type"] = "location_fail"
    turn_state["error_message"] = "Could you tell me which city or town you'd like the weather safety check for?"
    return {"turn_state": turn_state}
