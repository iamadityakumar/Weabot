import re
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel
from backend.agent_state import AgentState, SessionState, TurnState, assert_pending_request_consistency, canonical_activity_ids
from backend.llm_factory import llm_factory, clean_and_validate_location, is_quota_exhausted_error, TEMPORAL_STOP_WORDS, INVALID_LOCATION_WORDS
from backend.weather_client import CITY_STUBS
from backend.nodes.location_resolver import STOP
from backend.nodes.parse_turn import (
    extract_subject,
    extract_time_expression,
    is_followup_query,
    to_gerund,
    extract_candidate_activity,
    GERUND_MAP
)

GREET_RE = re.compile(
    r"^\s*(hi+|hey+|hello+|hola|namaste|yo|sup|good (morning|afternoon|evening)"
    r"|thanks?( you)?|thank you|ok(ay)?|cool|bye|good ?night|ok cool|okay cool)\W*$",
    re.I
)

ROUTER_PROMPT = (
    "You classify one user message for Weabot, an outdoor-activity safety assistant.\n"
    "Return JSON only.\n"
    "- weather_safety: asks whether weather conditions are safe or suitable for an\n"
    "  outdoor activity, trip, or person/pet outdoors, now or later, OR mentions a city/place name (e.g. \"Bhopal\", \"hey bhopal\").\n"
    "- smalltalk: greetings, thanks, goodbyes, \"how are you\".\n"
    "- about_bot: asks who you are or what you can do.\n"
    "- meta_session: refers to this conversation (summary, \"you said earlier\", change verdict).\n"
    "- out_of_scope: anything else (code, finance, recipes, news, general knowledge, etc.).\n"
    "A message that only contains a greeting or a bare word is NOT a place.\n"
    "place_text: copy the exact words naming a place from the message, else null.\n"
    "activity_text: the outdoor activity if stated, else null."
)

class Route(BaseModel):
    intent: Literal["weather_safety", "smalltalk", "about_bot", "meta_session", "out_of_scope"]
    place_text: Optional[str] = None      # must appear verbatim in the user message
    activity_text: Optional[str] = None

def canonicalize_activity(text: Optional[str]) -> Optional[str]:
    """
    Deterministically canonicalizes user activity expressions to official gerund IDs.
    Handles aliases: bike, biking, cycling, bicycle, two wheels, pedaling, ride -> cycling.
    """
    if not text:
        return None
    raw = text.strip().lower().strip(".,!?\"'")
    if not raw:
        return None

    # 1. Exact match in GERUND_MAP
    if raw in GERUND_MAP:
        return GERUND_MAP[raw]

    # 2. Longest alias match in text
    for alias in sorted(GERUND_MAP.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", raw):
            return GERUND_MAP[alias]

    # 3. Candidate activity extractor
    cand = extract_candidate_activity(text)
    if cand:
        return GERUND_MAP.get(cand, cand)

    return None

def extract_location_from_answer(message: str) -> Optional[str]:
    """
    Extracts and validates candidate city/town name from a user clarification response.
    Strips conversational prefixes, politeness fillers, and activities.
    """
    if not message:
        return None
    cleaned = message.strip().strip("'\".,;:!?()[]{}")
    if not cleaned:
        return None

    # Strip conversational prefixes
    cleaned = re.sub(r"^(?:in|at|near|around|for|actually|what about|how about|check|please)\s+", "", cleaned, flags=re.I).strip()
    # Strip trailing politeness
    cleaned = re.sub(r"\s+(?:please|thanks|thank you)\b.*$", "", cleaned, flags=re.I).strip()

    # If the user included an activity word, remove it to extract the location candidate
    # (e.g. "Xqzvbnmtrw cycling" -> "Xqzvbnmtrw")
    for act in sorted(GERUND_MAP.keys(), key=len, reverse=True):
        cleaned_without_act = re.sub(rf"\b{re.escape(act)}\b", "", cleaned, flags=re.I).strip()
        if cleaned_without_act and cleaned_without_act != cleaned:
            cleaned = cleaned_without_act
            break

    cleaned = cleaned.strip("'\".,;:!?()[]{}")
    if not cleaned:
        return None

    # Check known city stubs
    for c in CITY_STUBS:
        if c.lower() == cleaned.lower():
            return CITY_STUBS[c]["name"]

    # Check common cities
    common_cities = [
        "chicago", "los angeles", "berlin", "ottawa", "london", "paris",
        "tokyo", "new york", "san francisco", "miami", "seattle", "delhi",
        "mumbai", "bangalore"
    ]
    for c in common_cities:
        if c.lower() == cleaned.lower():
            return c.title()

    # Check validity via clean_and_validate_location
    val = clean_and_validate_location(cleaned)
    if val:
        return val

    # If it is a non-stopword alphabetic token, preserve for resolution attempt & honest failure
    if re.search(r"[A-Za-z]", cleaned) and cleaned.lower() not in STOP:
        return cleaned

    return None

def handle_pending_slot(state: AgentState, message: str) -> Dict[str, Any]:
    """
    Deterministic handler for pending slot clarifications.
    A clarification response is NOT a new user request; it is a partial update to the pending request.
    Only the missing slot is modified.
    """
    slot = state.get("awaiting_slot")
    pending = dict(state.get("pending_request") or {})
    raw_sess = state.get("session_state") or {}
    session_state: SessionState = {
        "last_good_location": raw_sess.get("last_good_location"),
        "last_activity": raw_sess.get("last_activity"),
        "last_subject": raw_sess.get("last_subject"),
        "decision_log": list(raw_sess.get("decision_log") or [])
    }

    if slot == "location":
        location = extract_location_from_answer(message)
        if not location:
            return {
                "route": "needs_location",
                "intent": "weather_safety",
                "awaiting_slot": "location",
                "pending_request": pending,
                "user_message": message,
                "session_state": session_state
            }

        pending["location"] = location
        if not pending.get("activity"):
            return {
                "route": "needs_activity",
                "intent": "weather_safety",
                "awaiting_slot": "activity",
                "pending_request": pending,
                "location": location,
                "place_text": location,
                "user_message": message,
                "session_state": session_state
            }

        orig_q = pending.get("original_query") or message
        act = pending.get("activity")
        res = {
            "route": "weather_safety",
            "intent": "weather_safety",
            "awaiting_slot": None,
            "pending_request": pending,
            "location": location,
            "activity": act,
            "place_text": location,
            "activity_text": act,
            "just_resolved_pending_slot": True,
            "user_message": message,
            "session_state": session_state,
            "turn_state": {
                "raw_query": orig_q,
                "dialogue_act": "new_query",
                "place_text": location,
                "raw_location": location,
                "activity_text": act,
                "activity": act,
                "activity_label": to_gerund(act),
                "subject": extract_subject(orig_q),
                "time_expression": pending.get("time_reference") or extract_time_expression(orig_q),
                "is_followup": False
            }
        }
        assert_pending_request_consistency(res)
        return res

    if slot == "activity":
        activity = canonicalize_activity(message)
        if not activity:
            return {
                "route": "needs_activity",
                "intent": "weather_safety",
                "awaiting_slot": "activity",
                "pending_request": pending,
                "user_message": message,
                "session_state": session_state
            }

        pending["activity"] = activity
        if not pending.get("location"):
            return {
                "route": "needs_location",
                "intent": "weather_safety",
                "awaiting_slot": "location",
                "pending_request": pending,
                "activity": activity,
                "activity_text": activity,
                "user_message": message,
                "session_state": session_state
            }

        orig_q = pending.get("original_query") or message
        loc = pending.get("location")
        res = {
            "route": "weather_safety",
            "intent": "weather_safety",
            "awaiting_slot": None,
            "pending_request": pending,
            "location": loc,
            "activity": activity,
            "place_text": loc,
            "activity_text": activity,
            "just_resolved_pending_slot": True,
            "user_message": message,
            "session_state": session_state,
            "turn_state": {
                "raw_query": orig_q,
                "dialogue_act": "new_query",
                "place_text": loc,
                "raw_location": loc,
                "activity_text": activity,
                "activity": activity,
                "activity_label": to_gerund(activity),
                "subject": extract_subject(orig_q),
                "time_expression": pending.get("time_reference") or extract_time_expression(orig_q),
                "is_followup": False
            }
        }
        assert_pending_request_consistency(res)
        return res

    # Fallback to normal routing if awaiting_slot unknown
    return normal_route(state, message, session_state)

def route_node(state: AgentState) -> Dict[str, Any]:
    """
    Router Gate Node Before Anything Else:
    1. Clarification-response branch BEFORE normal routing if awaiting_slot is set.
    2. Classifies incoming turns into:
       - weather_safety (with pending request state if slots are incomplete)
       - smalltalk
       - about_bot
       - meta_session
       - out_of_scope
    """
    requested_model = state.get("requested_model")
    effective_model, was_pre_switched = llm_factory.resolve_fallback_model(requested_model)
    quota_exhausted = was_pre_switched or bool(state.get("quota_exhausted", False))
    exhausted_model = state.get("exhausted_model") or (llm_factory.get_display_name(requested_model) if was_pre_switched else None)
    fallback_model = state.get("fallback_model") or (llm_factory.get_display_name(effective_model) if was_pre_switched else None)
    fallback_notice = state.get("fallback_notice") or (f"{exhausted_model} daily limit reached. Switched automatically to {fallback_model}." if was_pre_switched else None)

    messages = state.get("messages", [])
    if messages:
        latest = messages[-1]
        msg = latest.content if hasattr(latest, "content") else str(latest)
    else:
        msg = state.get("user_message") or ""

    msg_clean = msg.strip()
    msg_lower = msg_clean.lower()

    # Preserve or initialize session state
    raw_sess = state.get("session_state") or {}
    session_state: SessionState = {
        "last_good_location": raw_sess.get("last_good_location"),
        "last_activity": raw_sess.get("last_activity"),
        "last_subject": raw_sess.get("last_subject"),
        "decision_log": list(raw_sess.get("decision_log") or [])
    }

    def attach_quota_meta(res_dict: Dict[str, Any]) -> Dict[str, Any]:
        res_dict.setdefault("requested_model", effective_model)
        res_dict.setdefault("model_used", fallback_model if quota_exhausted else llm_factory.get_display_name(effective_model))
        res_dict.setdefault("quota_exhausted", quota_exhausted)
        res_dict.setdefault("exhausted_model", exhausted_model)
        res_dict.setdefault("fallback_model", fallback_model)
        res_dict.setdefault("fallback_notice", fallback_notice)
        return res_dict

    # 1. Clarification branch: check awaiting_slot BEFORE treating as new request
    awaiting = state.get("awaiting_slot")
    if awaiting:
        # Check if user explicitly changed topics
        if GREET_RE.match(msg_clean) or re.search(r"^\s*how are you\??\s*$", msg_clean, re.I):
            return attach_quota_meta({
                "intent": "smalltalk",
                "route": "smalltalk",
                "awaiting_slot": None,
                "pending_request": None,
                "place_text": None,
                "activity_text": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {"raw_query": msg, "dialogue_act": "smalltalk"}
            })
        if re.search(r"^\s*(who are you|what can you do|what are you)\??\s*$", msg_clean, re.I):
            return attach_quota_meta({
                "intent": "about_bot",
                "route": "about_bot",
                "awaiting_slot": None,
                "pending_request": None,
                "place_text": None,
                "activity_text": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {"raw_query": msg, "dialogue_act": "model_identity"}
            })
        if any(k in msg_lower for k in ["tell me a joke", "write a python", "best pizza", "tesla stock", "crypto"]):
            return attach_quota_meta({
                "intent": "out_of_scope",
                "route": "out_of_scope",
                "awaiting_slot": None,
                "pending_request": None,
                "place_text": None,
                "activity_text": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {"raw_query": msg, "dialogue_act": "out_of_scope"}
            })
        if re.search(r"\b(why\s+(?:did\s+you|did\s+it|is\s+that|would\s+you|do\s+you)|why\?|why\b\s*$|explain\b|which\s+sop|what\s+sop|you\s+said)\b", msg_lower):
            res = normal_route(state, msg, session_state, effective_model=effective_model, quota_exhausted=quota_exhausted, exhausted_model=exhausted_model, fallback_model=fallback_model, fallback_notice=fallback_notice)
            return attach_quota_meta(res)

        res = handle_pending_slot(state, msg)
        return attach_quota_meta(res)

    res = normal_route(state, msg, session_state, effective_model=effective_model, quota_exhausted=quota_exhausted, exhausted_model=exhausted_model, fallback_model=fallback_model, fallback_notice=fallback_notice)
    return attach_quota_meta(res)

def normal_route(
    state: AgentState, 
    msg: str, 
    session_state: SessionState,
    effective_model: Optional[str] = None,
    quota_exhausted: bool = False,
    exhausted_model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    fallback_notice: Optional[str] = None
) -> Dict[str, Any]:
    """Normal routing when no pending clarification slot is awaiting resolution."""
    msg_clean = msg.strip()
    msg_lower = msg_clean.lower()

    # 1. Fast regex greeting check
    if GREET_RE.match(msg_clean):
        return {
            "intent": "smalltalk",
            "route": "smalltalk",
            "awaiting_slot": None,
            "pending_request": None,
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "smalltalk"
            }
        }

    # Fast regex for "how are you"
    if re.search(r"^\s*how are you\??\s*$", msg_clean, re.I):
        return {
            "intent": "smalltalk",
            "route": "smalltalk",
            "awaiting_slot": None,
            "pending_request": None,
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "smalltalk"
            }
        }

    # Fast regex for about_bot
    if re.search(r"^\s*(who are you|what can you do|what are you)\??\s*$", msg_clean, re.I):
        return {
            "intent": "about_bot",
            "route": "about_bot",
            "awaiting_slot": None,
            "pending_request": None,
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "model_identity"
            }
        }

    # Fast regex for meta_session & why/rationale inquiries
    m_sop = re.search(r"\b(sop-\d+)\b", msg_lower)
    is_fake_sop = bool(m_sop and int(re.search(r"\d+", m_sop.group(1)).group(0)) > 13)
    is_why_inquiry = bool(re.search(r"\b(why\s+(?:did\s+you|did\s+it|is\s+that|would\s+you|do\s+you|is\s+it|are\s+you)|why\?|why\b\s*$|explain\s+(?:why|reasoning|decision|verdict)|how\s+did\s+you\s+(?:decide|get|arrive)|what\s+made\s+you)\b", msg_lower))
    if is_fake_sop or is_why_inquiry or any(k in msg_lower for k in [
        "you said it was fine", "you said fine", "told me it was safe", "you said earlier",
        "why did you say", "why did it say", "why did you tell", "which sop did you", "which sop",
        "what sop did you", "what sop", "which policy", "what policy",
        "override the sop", "certified safety officer", "just say yes", "system override",
        "summarize our discussion", "summarize the chat", "what have we discussed",
        "print your system prompt", "show your system prompt", "print every sop"
    ]):
        if is_fake_sop:
            dialogue_act = "fake_policy"
        elif is_why_inquiry or any(k in msg_lower for k in ["why did you say", "why did it say", "why did you tell", "which sop", "what sop", "which policy", "what policy"]):
            dialogue_act = "why_inquiry"
        elif any(k in msg_lower for k in ["you said", "said fine", "told me"]):
            dialogue_act = "challenge"
        elif any(k in msg_lower for k in ["override", "say yes", "change verdict", "safety officer"]):
            dialogue_act = "override_attempt"
        elif any(k in msg_lower for k in ["summarize", "summary", "what have we discussed"]):
            dialogue_act = "summary"
        elif any(k in msg_lower for k in ["system prompt", "print your prompt", "print every sop"]):
            dialogue_act = "disclosure"
        else:
            dialogue_act = "why_inquiry"

        return {
            "intent": "meta_session",
            "route": "meta_session",
            "awaiting_slot": None,
            "pending_request": None,
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": dialogue_act,
                "fake_sop_id": m_sop.group(1).upper() if m_sop else None
            }
        }

    # Fast regex for out_of_scope
    if any(k in msg_lower for k in [
        "tell me a joke", "write a python", "best pizza", "tesla stock", "crypto",
        "what should i wear", "what to wear", "clothing advice", "suggest an outfit",
        "air quality", "is the air fine", "air pollution", "has the imd issued", "imd warning",
        "low-pressure system", "low pressure system",
        "everest", "mount everest"
    ]):
        return {
            "intent": "out_of_scope",
            "route": "out_of_scope",
            "awaiting_slot": None,
            "pending_request": None,
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "out_of_scope"
            }
        }

    # 2. Extract potential city place if explicitly named
    known_place = None
    for c in CITY_STUBS:
        if re.search(rf"\b{re.escape(c)}\b", msg_clean, re.I):
            known_place = CITY_STUBS[c]["name"]
            break
    if not known_place:
        common_cities = [
            "chicago", "los angeles", "berlin", "ottawa", "london", "paris",
            "tokyo", "new york", "san francisco", "miami", "seattle", "delhi",
            "mumbai", "bangalore"
        ]
        for c in common_cities:
            if re.search(rf"\b{re.escape(c)}\b", msg_clean, re.I):
                known_place = c.title()
                break

    # 3. Check activity & follow-up signals
    has_activity = any(act in msg_lower for act in GERUND_MAP.keys())
    canonical_act = None
    for act in sorted(GERUND_MAP.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(act)}\b", msg_lower):
            canonical_act = GERUND_MAP[act]
            break

    is_followup = is_followup_query(msg)
    subject = extract_subject(msg)
    time_expr = extract_time_expression(msg)

    # Session carry-over for genuine follow-ups
    if is_followup:
        if not known_place and session_state.get("last_good_location"):
            known_place = session_state["last_good_location"].get("name")
        if not canonical_act and session_state.get("last_activity"):
            canonical_act = session_state.get("last_activity")

    # Time refinement turn (e.g. "This evening") with prior session state
    if not known_place and not canonical_act and time_expr and session_state.get("last_good_location") and session_state.get("last_activity"):
        known_place = session_state["last_good_location"].get("name")
        canonical_act = session_state.get("last_activity")
        is_followup = True

    # Explicit location replacement (e.g. "Actually Delhi.") carrying prior activity
    if known_place and not canonical_act and session_state.get("last_activity"):
        if any(w in msg_lower for w in ["actually", "what about", "how about", "instead", "in"]) or len(msg_clean.split()) <= 3:
            canonical_act = session_state.get("last_activity")

    # 4. Handle Pending Slots & Routing
    # Case A: Activity known, but location missing -> NEEDS_LOCATION
    if canonical_act and not known_place:
        cand_place = None
        # Check explicit preposition pattern first (e.g. "in Delhi", "around Paris")
        prep_m = re.search(r"\b(?:in|at|near|around)\s+([a-zA-Z\s\-]+?)(?:\s+(?:today|tomorrow|tonight|this|now|\d{1,2}(?:am|pm))|\?|$)", msg_clean, re.I)
        if prep_m:
            cand = clean_and_validate_location(prep_m.group(1))
            if cand:
                cand_place = cand

        # Only check shorthand queries (<= 3 words, e.g. "Xqzvbnmtrw cycling") if no preposition
        if not cand_place and len(msg_clean.strip().split()) <= 3:
            tokens = [w for w in re.findall(r"\b[A-Za-z0-9_\-]+\b", msg_clean) if w.lower() not in TEMPORAL_STOP_WORDS and w.lower() not in INVALID_LOCATION_WORDS]
            cand_tokens = [w for w in tokens if w.lower() not in GERUND_MAP and w.lower() not in INVALID_LOCATION_WORDS and len(w) >= 3]
            if cand_tokens:
                cand_str = " ".join(cand_tokens)
                cand_place = clean_and_validate_location(cand_str) or cand_str

        if cand_place:
            # Candidate location attempted: route to weather_safety for resolution attempt & honest failure
            res = {
                "intent": "weather_safety",
                "route": "weather_safety",
                "place_text": cand_place,
                "location": cand_place,
                "activity": canonical_act,
                "activity_text": canonical_act,
                "awaiting_slot": None,
                "pending_request": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {
                    "raw_query": msg,
                    "dialogue_act": "new_query",
                    "place_text": cand_place,
                    "raw_location": cand_place,
                    "activity_text": canonical_act,
                    "activity": canonical_act,
                    "activity_label": to_gerund(canonical_act),
                    "subject": subject,
                    "time_expression": time_expr,
                    "is_followup": False
                }
            }
            return res

        pending = {
            "original_query": msg,
            "intent": "weather_safety",
            "activity": canonical_act,
            "location": None,
            "time_reference": time_expr,
        }
        res = {
            "intent": "weather_safety",
            "route": "needs_location",
            "awaiting_slot": "location",
            "pending_request": pending,
            "activity": canonical_act,
            "location": None,
            "activity_text": canonical_act,
            "place_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "new_query",
                "activity": canonical_act,
                "activity_label": to_gerund(canonical_act),
                "subject": subject,
                "time_expression": time_expr,
                "is_followup": False
            }
        }
        assert_pending_request_consistency(res)
        return res

    # Case B: Location known, but activity missing -> NEEDS_ACTIVITY
    if known_place and not canonical_act:
        # Check if query is asking for meteorological telemetry without activity
        if any(k in msg_lower for k in ["wind speed", "wind in", "temperature", "uv index", "humidity", "weather in", "forecast in", "give me the wind", "what is the wind"]):
            canonical_act = "general outdoor activity"
        else:
            pending = {
                "original_query": msg,
                "intent": "weather_safety",
                "activity": None,
                "location": known_place,
                "time_reference": time_expr,
            }
            res = {
                "intent": "weather_safety",
                "route": "needs_activity",
                "awaiting_slot": "activity",
                "pending_request": pending,
                "location": known_place,
                "activity": None,
                "place_text": known_place,
                "activity_text": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {
                    "raw_query": msg,
                    "dialogue_act": "new_query",
                    "place_text": known_place,
                    "raw_location": known_place,
                    "subject": subject,
                    "time_expression": time_expr,
                    "is_followup": False
                }
            }
            assert_pending_request_consistency(res)
            return res

    # Case C: Both location and activity known -> WEATHER_SAFETY
    if known_place and canonical_act:
        res = {
            "intent": "weather_safety",
            "route": "weather_safety",
            "awaiting_slot": None,
            "pending_request": None,
            "location": known_place,
            "activity": canonical_act,
            "place_text": known_place,
            "activity_text": canonical_act,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "new_query",
                "place_text": known_place,
                "raw_location": known_place,
                "activity_text": canonical_act,
                "activity": canonical_act,
                "activity_label": to_gerund(canonical_act),
                "subject": subject,
                "time_expression": time_expr,
                "is_followup": is_followup
            }
        }
        assert_pending_request_consistency(res)
        return res

    # Check for invalid candidate location word (e.g. "Xqzvbnmtrw" alone or with prior session)
    raw_tokens = re.findall(r"\b[A-Za-z0-9_\-]+\b", msg_clean)
    if len(raw_tokens) == 1 and raw_tokens[0].lower() not in STOP and not GREET_RE.match(msg_clean):
        # Single candidate token: attempt location resolution in weather_safety and fail honestly
        cand = raw_tokens[0]
        act = session_state.get("last_activity") or "general outdoor activity"
        return {
            "intent": "weather_safety",
            "route": "weather_safety",
            "place_text": cand,
            "location": cand,
            "activity": act,
            "activity_text": act,
            "awaiting_slot": None,
            "pending_request": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "new_query",
                "place_text": cand,
                "raw_location": cand,
                "activity_text": act,
                "activity": act,
                "activity_label": to_gerund(act),
                "subject": subject,
                "time_expression": time_expr,
                "is_followup": False
            }
        }

    # 5. Structured LLM Router call with fail-closed guarantee & quota fallback
    chosen_model = effective_model or state.get("requested_model") or "gemini-3.8-flash"
    router_llm = llm_factory.get_llm(chosen_model)
    r: Optional[Route] = None

    def wrap_res(d: Dict[str, Any]) -> Dict[str, Any]:
        d.setdefault("requested_model", chosen_model)
        d.setdefault("model_used", fallback_model if quota_exhausted else llm_factory.get_display_name(chosen_model))
        d.setdefault("quota_exhausted", quota_exhausted)
        d.setdefault("exhausted_model", exhausted_model)
        d.setdefault("fallback_model", fallback_model)
        d.setdefault("fallback_notice", fallback_notice)
        return d

    if router_llm and hasattr(router_llm, "with_structured_output"):
        try:
            structured_router = router_llm.with_structured_output(Route)
            r = structured_router.invoke([
                ("system", ROUTER_PROMPT),
                ("human", msg)
            ])
        except Exception as e:
            print(f"[RouterNode] Router LLM call error: {e}")
            if is_quota_exhausted_error(e):
                llm_factory.mark_model_exhausted(chosen_model, reason=f"router invoke 429: {e}")
                next_model, _ = llm_factory.resolve_fallback_model(chosen_model)
                quota_exhausted = True
                exhausted_model = llm_factory.get_display_name(chosen_model)
                fallback_model = llm_factory.get_display_name(next_model)
                fallback_notice = f"{exhausted_model} daily limit reached. Switched automatically to {fallback_model}."
                chosen_model = next_model

                fallback_llm = llm_factory.get_llm(next_model)
                if fallback_llm and hasattr(fallback_llm, "with_structured_output"):
                    try:
                        fb_router = fallback_llm.with_structured_output(Route)
                        r = fb_router.invoke([
                            ("system", ROUTER_PROMPT),
                            ("human", msg)
                        ])
                        print(f"[RouterNode] Fallback router succeeded with model: {fallback_model}")
                    except Exception as fb_err:
                        print(f"[RouterNode] Fallback router also failed: {fb_err}")
                        if is_quota_exhausted_error(fb_err):
                            llm_factory.mark_model_exhausted(next_model, reason=f"fallback router 429: {fb_err}")

    if r is None:
        # Deterministic route classification fallback
        clean_cand_act = extract_candidate_activity(msg)
        clean_cand_place = known_place
        if not clean_cand_place:
            prep_m = re.search(r"\b(?:in|at|near|around)\s+([a-zA-Z\s\-]+?)(?:\s+(?:today|tomorrow|tonight|this|now|\d{1,2}(?:am|pm))|\?|$)", msg_clean, re.I)
            if prep_m:
                clean_cand_place = clean_and_validate_location(prep_m.group(1))
            elif len(msg_clean.strip().split()) <= 3:
                tokens = [w for w in re.findall(r"\b[A-Za-z0-9_\-]+\b", msg_clean) if w.lower() not in TEMPORAL_STOP_WORDS and w.lower() not in INVALID_LOCATION_WORDS]
                cand_tokens = [w for w in tokens if w.lower() not in GERUND_MAP and w.lower() not in INVALID_LOCATION_WORDS and len(w) >= 3]
                if cand_tokens:
                    cand_str = " ".join(cand_tokens)
                    clean_cand_place = clean_and_validate_location(cand_str) or cand_str

        is_oos_task = any(k in msg_lower for k in ["code", "python", "joke", "pizza", "stock", "shares", "crypto", "recipe", "invest"])

        if is_why_inquiry:
            intent = "meta_session"
            place = None
            act_cand = None
        elif re.search(r"\b(hello|hi+|hey+|greetings|good morning|good evening|good afternoon)\b", msg_lower) and not clean_cand_act and not clean_cand_place:
            intent = "smalltalk"
            place = None
            act_cand = None
        elif any(b in msg_lower for b in ["who are you", "what are you", "what can you do", "help me"]):
            intent = "about_bot"
            place = None
            act_cand = None
        elif (clean_cand_act or clean_cand_place) and not is_oos_task:
            intent = "weather_safety"
            place = clean_cand_place
            act_cand = clean_cand_act
        else:
            return wrap_res({
                "intent": "out_of_scope",
                "route": "out_of_scope",
                "place_text": None,
                "activity_text": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {
                    "raw_query": msg,
                    "dialogue_act": "out_of_scope"
                }
            })
    else:
        intent = r.intent
        raw_place = r.place_text if r.place_text and r.place_text.lower() in msg.lower() else None
        place = clean_and_validate_location(raw_place) or known_place
        act_cand = r.activity_text or extract_candidate_activity(msg)

    is_out_of_scope_task = any(k in msg_lower for k in ["code", "python", "joke", "pizza", "stock", "shares", "crypto", "recipe", "invest"])
    if place and not is_out_of_scope_task and intent != "meta_session":
        intent = "weather_safety"

    dialogue_act = "new_query"
    if intent == "meta_session":
        dialogue_act = "challenge"

    if not act_cand and is_followup and session_state.get("last_activity"):
        act_cand = session_state.get("last_activity")
    canonical_act = GERUND_MAP.get(act_cand, act_cand) if act_cand else None
    act_label = to_gerund(canonical_act) if canonical_act else None

    # Handle slot requirements from LLM classification
    if intent == "weather_safety":
        if canonical_act and not place:
            pending = {
                "original_query": msg,
                "intent": "weather_safety",
                "activity": canonical_act,
                "location": None,
                "time_reference": time_expr,
            }
            res = wrap_res({
                "intent": "weather_safety",
                "route": "needs_location",
                "awaiting_slot": "location",
                "pending_request": pending,
                "activity": canonical_act,
                "location": None,
                "activity_text": canonical_act,
                "place_text": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {
                    "raw_query": msg,
                    "dialogue_act": "new_query",
                    "activity": canonical_act,
                    "activity_label": act_label,
                    "subject": subject,
                    "time_expression": time_expr,
                    "is_followup": False
                }
            })
            assert_pending_request_consistency(res)
            return res
        elif place and not canonical_act:
            pending = {
                "original_query": msg,
                "intent": "weather_safety",
                "activity": None,
                "location": place,
                "time_reference": time_expr,
            }
            res = wrap_res({
                "intent": "weather_safety",
                "route": "needs_activity",
                "awaiting_slot": "activity",
                "pending_request": pending,
                "location": place,
                "activity": None,
                "place_text": place,
                "activity_text": None,
                "user_message": msg,
                "session_state": session_state,
                "turn_state": {
                    "raw_query": msg,
                    "dialogue_act": "new_query",
                    "place_text": place,
                    "raw_location": place,
                    "subject": subject,
                    "time_expression": time_expr,
                    "is_followup": False
                }
            })
            assert_pending_request_consistency(res)
            return res

    res = wrap_res({
        "intent": intent,
        "route": intent,
        "place_text": place,
        "location": place,
        "activity_text": canonical_act,
        "activity": canonical_act,
        "user_message": msg,
        "session_state": session_state,
        "turn_state": {
            "raw_query": msg,
            "dialogue_act": dialogue_act,
            "place_text": place,
            "raw_location": place,
            "activity_text": canonical_act,
            "activity": canonical_act,
            "activity_label": act_label,
            "subject": subject,
            "time_expression": time_expr,
            "is_followup": is_followup
        }
    })
    if intent == "weather_safety":
        assert_pending_request_consistency(res)
    return res
