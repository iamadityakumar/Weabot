import re
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel
from backend.agent_state import AgentState, SessionState, TurnState
from backend.llm_factory import llm_factory
from backend.weather_client import CITY_STUBS
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

def route_node(state: AgentState) -> Dict[str, Any]:
    """
    Fix 1: Router Node Before Anything Else
    Classifies incoming user turn into:
    - weather_safety
    - smalltalk
    - about_bot
    - meta_session
    - out_of_scope
    """
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

    # 1. Fast regex greeting check
    if GREET_RE.match(msg_clean):
        return {
            "intent": "smalltalk",
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
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "model_identity"
            }
        }

    # Fast regex for meta_session
    m_sop = re.search(r"\b(sop-\d+)\b", msg_lower)
    is_fake_sop = bool(m_sop and int(re.search(r"\d+", m_sop.group(1)).group(0)) > 13)
    if is_fake_sop or any(k in msg_lower for k in [
        "you said it was fine", "you said fine", "told me it was safe", "you said earlier",
        "override the sop", "certified safety officer", "just say yes", "system override",
        "summarize our discussion", "summarize the chat", "what have we discussed",
        "print your system prompt", "show your system prompt", "print every sop"
    ]):
        if is_fake_sop:
            dialogue_act = "fake_policy"
        elif any(k in msg_lower for k in ["you said", "said fine", "told me"]):
            dialogue_act = "challenge"
        elif any(k in msg_lower for k in ["override", "say yes", "change verdict", "safety officer"]):
            dialogue_act = "override_attempt"
        elif any(k in msg_lower for k in ["summarize", "summary", "what have we discussed"]):
            dialogue_act = "summary"
        elif any(k in msg_lower for k in ["system prompt", "print your prompt", "print every sop"]):
            dialogue_act = "disclosure"
        else:
            dialogue_act = "challenge"

        return {
            "intent": "meta_session",
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
        if re.search(rf"\b{c}\b", msg_clean, re.I):
            known_place = c.capitalize()
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

    # 3. Check obvious weather inquiries / follow-ups
    has_activity = any(act in msg_lower for act in GERUND_MAP.keys())
    is_followup = is_followup_query(msg)
    subject = extract_subject(msg)
    time_expr = extract_time_expression(msg)

    # If query has a place or recognized activity or is a clear follow-up
    if known_place or has_activity or (is_followup and session_state.get("last_good_location")):
        act_text = None
        for act in sorted(GERUND_MAP.keys(), key=len, reverse=True):
            if act in msg_lower:
                act_text = act
                break

        if not act_text and is_followup and session_state.get("last_activity"):
            act_text = session_state.get("last_activity")

        # Canonicalize activity using GERUND_MAP if applicable
        canonical_act = GERUND_MAP.get(act_text, act_text) if act_text else None
        act_label = to_gerund(canonical_act) if canonical_act else None

        return {
            "intent": "weather_safety",
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
                "activity_label": act_label,
                "subject": subject,
                "time_expression": time_expr,
                "is_followup": is_followup
            }
        }

    # 4. Structured LLM Router call with fail-closed guarantee
    router_llm = llm_factory.get_llm(state.get("requested_model"))
    if not router_llm or not hasattr(router_llm, "with_structured_output"):
        return {
            "intent": "out_of_scope",
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "out_of_scope"
            }
        }

    try:
        structured_router = router_llm.with_structured_output(Route)
        r: Route = structured_router.invoke([
            ("system", ROUTER_PROMPT),
            ("human", msg)
        ])
    except Exception as e:
        print(f"[RouterNode] Router LLM failed ({e}), failing closed to out_of_scope.")
        return {
            "intent": "out_of_scope",
            "place_text": None,
            "activity_text": None,
            "user_message": msg,
            "session_state": session_state,
            "turn_state": {
                "raw_query": msg,
                "dialogue_act": "out_of_scope"
            }
        }

    intent = r.intent
    place = r.place_text if r.place_text and r.place_text.lower() in msg.lower() else known_place

    # Route bare place names or place presence to weather_safety
    is_out_of_scope_task = any(k in msg_lower for k in ["code", "python", "joke", "pizza", "stock", "shares", "crypto", "recipe", "invest"])
    if place and not is_out_of_scope_task and intent != "meta_session":
        intent = "weather_safety"

    dialogue_act = "new_query"
    if intent == "meta_session":
        dialogue_act = "challenge"

    act_cand = r.activity_text or candidate_act
    if not act_cand and is_followup and session_state.get("last_activity"):
        act_cand = session_state.get("last_activity")
    canonical_act = GERUND_MAP.get(act_cand, act_cand) if act_cand else None
    act_label = to_gerund(canonical_act) if canonical_act else None

    return {
        "intent": intent,
        "place_text": place,
        "activity_text": canonical_act,
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
    }
