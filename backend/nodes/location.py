import asyncio
import re
from typing import Dict, Any, Optional
from backend.agent_state import AgentState
from backend.weather_client import WeatherClient, GeocodingError

_weather_client = WeatherClient()

def get_weather_client() -> WeatherClient:
    return _weather_client

def check_location_present(state: AgentState) -> str:
    """Routing function after intake."""
    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")
    query_lower = user_query.lower()
    # 0. Out-of-scope check (stocks/finance, extreme mountaineering, IMD/synoptic alerts, prompt leak)
    out_of_scope_patterns = [
        "tesla", "stock", "shares", "crypto", "bitcoin", "invest in", "buy stock",
        "everest", "mount everest", "k2", "annapurna",
        "has the imd issued", "imd issued a warning", "imd warning been issued", "imd alert been issued", "imd issued an alert",
        "low-pressure system", "low pressure system", "cyclonic storm", "depression over",
        "system prompt", "internal prompt", "every sop", "all sops"
    ]
    if any(k in query_lower for k in out_of_scope_patterns):
        return "out_of_scope"

    # 0.1 Model identity query check
    model_query_patterns = [
        "what model are you", "which model are you", "what model is this",
        "which model is this", "what ai are you", "what ai is this", "who are you",
        "what model do you use", "which model do you use", "what model are you using",
        "which model are you using", "what llm are you", "which llm are you",
        "what is your model", "what is the model", "tell me your model"
    ]
    if any(k in query_lower for k in model_query_patterns):
        return "model_identity"

    # If the user message contains NO Latin alphabetic characters (e.g. emoji-only or symbols)
    if not re.search(r"[A-Za-z]", user_query):
        return "ask_location"

    # If the user query is in Devanagari script
    if re.search(r"[\u0900-\u097F]", user_query):
        return "ask_location"

    # If user explicitly asked "here" without context, ask for location
    session_facts = state.get("session_facts") or {}
    if any(k in query_lower for k in ["what's it like here", "what is it like here", "weather here"]):
        if not session_facts.get("location_name"):
            return "ask_location"

    intent = state.get("extracted_intent") or {}
    location = intent.get("location")

    if not location or not str(location).strip():
        # Check if we already have a location from prior turns
        if session_facts.get("location_name"):
            return "resolve_location"
        return "ask_location"
    return "resolve_location"

def ask_location_node(state: AgentState) -> Dict[str, Any]:
    """Deterministic prompt asking the user for their location in a peer guardian tone."""
    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")
    query_lower = user_query.lower()
    intent = state.get("extracted_intent") or {}
    activity = intent.get("activity")

    # Devanagari limitation notice
    if re.search(r"[\u0900-\u097F]", user_query):
        msg = (
            "नमस्ते! Weabot currently supports queries in English and Latin transliteration (e.g. 'Bhopal'). "
            "Non-Latin Devanagari script is not currently parsed. "
            "Please enter your city name in Latin characters (e.g., 'Bhopal') so I can check live weather safety for you! 🌤️"
        )
        return {
            "final_response": msg,
            "sop_citations": [],
            "error_message": None,
            "verdict": {
                "status": "UNCOVERED",
                "title": "Location Required",
                "severity": "low",
                "summary": "Non-Latin script detected. Please specify location in Latin characters.",
                "activity": activity or "outdoor activity",
                "location": "Not specified"
            }
        }

    # IMD / Synoptic feed scope disclosure
    if any(k in query_lower for k in ["imd", "synoptic", "low-pressure", "low pressure", "depression", "cyclone"]):
        msg = (
            "⚠️ **Data Source Notice**: Weabot is powered by physical telemetry from Open-Meteo numerical weather prediction models "
            "and does not have an active data integration with the India Meteorological Department (IMD) or national synoptic early-warning feeds. "
            "Because we cannot verify official government bulletins or synoptic warnings, we strictly refrain from guessing or inventing alerts. "
            "Please check https://mausam.imd.gov.in for official IMD alerts.\n\n"
            "Could you tell me which specific recognized city or town you'd like the local weather and safety check for? 🌤️"
        )
        return {
            "final_response": msg,
            "sop_citations": [],
            "error_message": None,
            "verdict": {
                "status": "UNCOVERED",
                "title": "Location Required · Synoptic Feed Unavailable",
                "severity": "low",
                "summary": "Weabot does not ingest IMD synoptic warning feeds. Please specify a recognized city.",
                "activity": activity or "outdoor activity",
                "location": "Not specified"
            }
        }

    if activity and activity.lower() not in ("outdoor activity", "this outdoor activity", "your activity", "none"):
        msg = (
            f"Hey there! I'd love to help keep you safe while {activity}. "
            "Could you tell me which city or town you'll be in? "
            "Once I know where you are, I'll check the live weather and make sure everything looks safe for you! 🌤️"
        )
    else:
        msg = (
            "Hey there! Could you please tell me which city or town you'd like the weather report or safety check for? "
            "Once I know your location, I'll pull the live conditions and check everything for you! 🌤️"
        )
    return {
        "final_response": msg,
        "sop_citations": [],
        "error_message": None,
        "verdict": {
            "status": "UNCOVERED",
            "title": "Location Required",
            "severity": "low",
            "summary": "Please specify a city or town to retrieve verified live weather and safety advisories.",
            "activity": activity or "outdoor activity",
            "location": "Not specified"
        }
    }

def model_identity_node(state: AgentState) -> Dict[str, Any]:
    """Provides clear, direct attribution of the active AI model and engine architecture."""
    from backend.config import settings
    requested_model = state.get("requested_model") or settings.GEMINI_MODEL
    norm = str(requested_model).lower()

    if "3.8" in norm or "flash" in norm:
        display_name = "Gemini 3.8 Flash (Google DeepMind)"
    elif "pro" in norm:
        display_name = "Gemini 1.5 Pro (Google DeepMind)"
    elif "120b" in norm:
        display_name = "GPT-OSS 120B (Groq Cloud)"
    elif "20b" in norm:
        display_name = "GPT-OSS 20B (Groq Cloud)"
    elif "qwen" in norm or "groq" in norm:
        display_name = "Qwen 3.8 27B (Groq Cloud)"
    elif "deterministic" in norm:
        display_name = "Open-Meteo Deterministic (Safety Graph Engine)"
    else:
        display_name = requested_model

    msg = (
        f"🤖 **Active AI Reasoning Model**: Currently operating with **{display_name}**.\n\n"
        "I am **Weabot**, an Outdoor Activity Safety Advisor. I evaluate live numerical telemetry "
        "from Open-Meteo against strict Standard Operating Procedures (SOPs).\n\n"
        "You can switch my underlying model at any time using the model selector dropdown below. "
        "Which city and activity would you like me to check safety for? 🌤️"
    )
    return {
        "final_response": msg,
        "sop_citations": [],
        "error_message": None,
        "verdict": {
            "status": "INFO",
            "title": f"Active Model · {display_name}",
            "severity": "low",
            "summary": f"Operating with {display_name}.",
            "activity": "system",
            "location": "cloud"
        }
    }

async def location_resolve_node(state: AgentState) -> Dict[str, Any]:
    """
    Resolve location text via Open-Meteo geocoding.
    Tests candidate and prefixes against geocoding; falls back to prior session location for follow-ups;
    and routes unresolvable names to unknown_location error.
    """
    messages = state.get("messages", [])
    user_query = messages[-1].content if messages and hasattr(messages[-1], "content") else (str(messages[-1]) if messages else "")
    query_lower = user_query.lower()

    intent = state.get("extracted_intent") or {}
    raw_location = intent.get("location")
    session_facts = dict(state.get("session_facts") or {})

    # Temporal words that indicate a follow-up rather than a new city
    TEMPORAL_MARKERS = [
        "evening", "tomorrow", "morning", "afternoon", "2am", "2 am", "tonight", "later",
        "instead", "earlier", "yesterday", "this week", "next week", "next month", "what about",
        "how about", "can i", "is it safe", "is it okay", "should i", "you said", "anything changed"
    ]
    is_temporal_followup = any(m in query_lower for m in TEMPORAL_MARKERS)

    # 1. Build candidates to test against geocoding
    candidates = []
    if raw_location and str(raw_location).strip():
        loc_str = str(raw_location).strip()
        candidates.append(loc_str)
        # Prefix trimming by words: e.g. "Aurangabad today" -> ["Aurangabad today", "Aurangabad"]
        words = loc_str.split()
        if len(words) > 1:
            for i in range(len(words) - 1, 0, -1):
                prefix = " ".join(words[:i]).strip()
                if len(prefix) >= 3 and prefix.lower() not in [c.lower() for c in candidates]:
                    candidates.append(prefix)

    from backend.llm_factory import INVALID_LOCATION_WORDS, TEMPORAL_STOP_WORDS

    # Also search for phrases following prepositions in the raw user query
    matches = re.finditer(r"\b(?:in|around|near|at)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", user_query, re.IGNORECASE)
    for m in matches:
        phrase = m.group(1).strip()
        if phrase and phrase.lower() not in [c.lower() for c in candidates]:
            candidates.append(phrase)
            p_words = phrase.split()
            if len(p_words) > 1:
                for i in range(len(p_words) - 1, 0, -1):
                    p_prefix = " ".join(p_words[:i]).strip()
                    if len(p_prefix) >= 3 and p_prefix.lower() not in [c.lower() for c in candidates]:
                        candidates.append(p_prefix)

    # 2. Try geocoding each candidate
    resolved_geo = None
    for cand in candidates:
        cand_lower = cand.lower().strip()
        if (
            cand_lower in INVALID_LOCATION_WORDS
            or cand_lower in TEMPORAL_STOP_WORDS
            or all(w in TEMPORAL_STOP_WORDS or w in INVALID_LOCATION_WORDS for w in cand_lower.split())
        ):
            continue
        try:
            geo = await _weather_client.geocode(cand)
            if geo and geo.get("latitude") is not None:
                resolved_geo = geo
                break
        except GeocodingError:
            continue

    # 3. If geocoding succeeded with a candidate
    if resolved_geo:
        name = resolved_geo["name"]
        admin1 = resolved_geo.get("admin1")
        country = resolved_geo.get("country")
        display_name = f"{name} ({admin1}, {country})" if admin1 and country else (f"{name} ({admin1})" if admin1 else name)

        session_facts["location_name"] = name
        session_facts["location_display"] = display_name
        session_facts["latitude"] = resolved_geo["latitude"]
        session_facts["longitude"] = resolved_geo["longitude"]

        if not session_facts.get("primary_location"):
            session_facts["primary_location"] = name

        return {
            "session_facts": session_facts,
            "error_message": None,
            "error_type": None
        }

    # 4. If geocoding failed, check if this is a follow-up in an existing session
    if session_facts.get("location_name") and (is_temporal_followup or not raw_location):
        # Keep existing verified location
        return {
            "session_facts": session_facts,
            "error_message": None,
            "error_type": None
        }

    # 5. Geocoding failed and no valid prior session location exists
    unknown_name = raw_location or user_query.strip()
    return {
        "error_message": f"Could not resolve location: '{unknown_name}'",
        "error_type": "unknown_location",
        "unknown_location_name": unknown_name
    }

def check_geocode_status(state: AgentState) -> str:
    """Routing function after geocoding."""
    if state.get("error_type") == "unknown_location" or state.get("error_message"):
        return "failure"
    return "fetch_weather"
