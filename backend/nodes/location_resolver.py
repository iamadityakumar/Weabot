import re
import difflib
from typing import Dict, Any, Optional
from backend.agent_state import AgentState, SafetyStatus
from backend.nodes.location import get_weather_client
from backend.weather_client import GeocodingError

STOP = {"hey", "hi", "hello", "ok", "yes", "no", "now", "today", "here", "there", "test"}
sim = lambda a, b: difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def resolve_location_node(state: AgentState) -> Dict[str, Any]:
    """
    Fix 2: Geocode Guard & Location Resolution
    - Guard stops bare greetings from resolving (e.g. 'Hey' -> Heijplaat).
    - Requires similarity >= 0.8 between query and geocoded name.
    - Weather runs only when intent is weather_safety and a verified place exists.
    - If question has weather intent but no place, asks for one.
    - If it has a place but no activity, asks what activity.
    """
    turn_state = dict(state.get("turn_state") or {})
    session_state = state.get("session_state") or {}
    last_good = session_state.get("last_good_location")
    user_query = turn_state.get("raw_query") or state.get("user_message") or ""
    query_lower = user_query.lower()
    is_followup = turn_state.get("is_followup", False)

    # 1. Devanagari script check
    if re.search(r"[\u0900-\u097F]", user_query):
        turn_state["error_type"] = "location_fail"
        turn_state["error_message"] = (
            "Weabot currently supports queries in English and Latin transliteration (e.g. 'Bhopal'). "
            "Non-Latin Devanagari script is not currently parsed. "
            "Please specify your location in Latin characters so I can check live weather safety for you."
        )
        return {"turn_state": turn_state}

    # 2. Coordinates / open-ocean check (#27)
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

    # 3. Extract place candidate: state location, pending_request, place_text, or preposition
    q = (state.get("location") or (state.get("pending_request") or {}).get("location") or state.get("place_text") or turn_state.get("place_text") or turn_state.get("raw_location") or "").strip()
    if not q:
        from backend.llm_factory import clean_and_validate_location
        # Prioritize 'in', 'around', 'near' over 'at' (which often attaches to times e.g. 'at 1 PM' or venues 'at the park')
        m_prep = re.search(r"\b(?:in|around|near)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", user_query, re.IGNORECASE)
        if not m_prep:
            m_prep = re.search(r"\bat\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", user_query, re.IGNORECASE)
        if m_prep:
            cand = m_prep.group(1).strip()
            cand = re.sub(r"\b(today|tomorrow|yesterday|now|right now|this|next)\b.*$", "", cand, flags=re.IGNORECASE).strip()
            val = clean_and_validate_location(cand)
            if val:
                q = val
            elif not m_prep.group(0).lower().startswith("in"):
                m_in = re.search(r"\bin\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", user_query, re.IGNORECASE)
                if m_in:
                    c_in = re.sub(r"\b(today|tomorrow|yesterday|now|right now|this|next)\b.*$", "", m_in.group(1), flags=re.IGNORECASE).strip()
                    val_in = clean_and_validate_location(c_in)
                    if val_in:
                        q = val_in
            if not q:
                q = cand

    if not q and not is_followup:
        from backend.nodes.parse_turn import GERUND_MAP
        # Find candidate location words (e.g. "Xqzvbnmtrw cycling", "Delhi cycling")
        skip_words = set(STOP) | {
            "what", "about", "how", "and", "or", "is", "it", "safe", "safely", "can", "i", "we", "for",
            "the", "a", "an", "to", "go", "good", "day", "tonight", "today", "tomorrow", "morning",
            "evening", "afternoon", "night", "now", "later", "this", "my", "your", "with", "would",
            "should", "be", "fine", "ok", "okay", "tell", "me", "if", "ride", "riding", "instead", "better",
            "weather", "forecast", "give", "check", "has", "anything", "changed", "since", "you", "last", "checked"
        }
        raw_tokens = re.findall(r"\b[A-Za-z0-9_\-]+\b", user_query)
        non_act_tokens = [
            t for t in raw_tokens
            if t.lower() not in GERUND_MAP
            and t.lower() not in skip_words
            and not any(act in t.lower() for act in ["cycling", "walking", "running", "jogging", "driving", "gathering"])
        ]
        if non_act_tokens and len(non_act_tokens) <= 3:
            cand_place = " ".join(non_act_tokens)
            from backend.llm_factory import clean_and_validate_location
            val = clean_and_validate_location(cand_place)
            q = val if val else cand_place

    # Relative spatial pronouns are carryovers, not place names
    if q and re.match(r"^(here|there|around here|over there|there instead|here instead)$", q, re.I):
        q = ""

    # 4. Check STOP words and length
    if len(q) < 3 or q.lower() in STOP:
        if is_followup and last_good:
            resolved = dict(last_good)
        else:
            turn_state["error_type"] = "location_fail"
            turn_state["error_message"] = "Could you tell me which city or town you'd like the weather safety check for?"
            return {"turn_state": turn_state}
    else:
        # Geocode with top-5 hits and similarity ranking
        weather_client = get_weather_client()
        hits = await weather_client.geocode_hits(q, count=5)
        best = max(hits, key=lambda h: sim(q, h["name"]), default=None)
        if not best or sim(q, best["name"]) < 0.8:
            turn_state["error_type"] = "location_fail"
            turn_state["error_message"] = (
                f"Could not resolve location: '{q}'. "
                "Could not find that place. Please check spelling or enter a recognized city or town."
            )
            return {"turn_state": turn_state}

        name = best["name"]
        admin1 = best.get("admin1")
        country = best.get("country")
        display = f"{name} ({admin1}, {country})" if admin1 and country else (f"{name} ({admin1})" if admin1 else name)

        resolved = {
            "name": name,
            "display": display,
            "latitude": best["latitude"],
            "longitude": best["longitude"],
            "timezone": best.get("timezone", "UTC"),
            "admin1": admin1,
            "country": country
        }

    turn_state["resolved_location"] = resolved

    # 5. Check if activity is specified
    # "If it has a place but no activity, ask what activity."
    from backend.nodes.parse_turn import GERUND_MAP, to_gerund, extract_candidate_activity
    act = state.get("activity_text") or turn_state.get("activity_text") or turn_state.get("activity")
    if not act and is_followup and session_state.get("last_activity"):
        act = session_state.get("last_activity")

    if not act:
        act = extract_candidate_activity(user_query)

    if not act or str(act).strip().lower() in ("none", "null", "all", "any"):
        if any(k in query_lower for k in ["wind speed", "wind in", "temperature", "uv index", "humidity", "weather in", "forecast in", "give me the wind", "what is the wind"]):
            act = "general outdoor activity"
        else:
            turn_state["error_type"] = "ask_activity"
            turn_state["error_message"] = f"What outdoor activity are you planning in {resolved['name']}? Tell me what you'd like to do (e.g., cycling, walking, running, outdoor gathering), and I'll check live safety conditions for you."
            return {"turn_state": turn_state}

    canonical_act = GERUND_MAP.get(act, act) if act else act
    turn_state["activity"] = canonical_act
    turn_state["activity_label"] = to_gerund(canonical_act)
    return {
        "turn_state": turn_state,
        "location": resolved["name"],
        "activity": canonical_act
    }
