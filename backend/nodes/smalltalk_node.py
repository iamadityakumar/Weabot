import re
from typing import Dict, Any
from backend.agent_state import AgentState, SafetyStatus
from backend.llm_factory import llm_factory

SMALLTALK_PROMPT = (
    "You are Weabot, a friendly outdoor-safety assistant. The user sent a greeting or "
    "casual remark. Reply in one or two warm sentences and invite an outdoor-safety "
    "question. Do not mention weather values, locations, forecasts or advice."
)

FALLBACK_GREETING = (
    "Hello! I'm Weabot, your outdoor-safety assistant. Tell me an activity and a place, "
    "and I'll check live conditions against our approved safety guidelines!"
)

# Reject any digit-plus-unit pattern (C, km/h, mm, mph), weather words, and advice directives
GUARD_DIGIT_UNIT = re.compile(r"\b\d+\s*(?:°?[CcFf]|km/?h|mm|mph|m/s|%)\b")
GUARD_WEATHER_WORDS = re.compile(r"\b(temperature|forecast|degrees?|celsius|rain|wind|humidity|uv|precipitation|snow|storm)\b", re.I)
GUARD_ADVICE_WORDS = re.compile(r"\b(safe to|proceed with caution|enjoy|you should wear|bring an umbrella|dress warmly|wear|pack)\b", re.I)

def smalltalk_node(state: AgentState) -> Dict[str, Any]:
    """
    Fix 3: Smalltalk Node
    Replies naturally using a small LLM call (zero weather data in context).
    Enforces output guards rejecting weather data, units, and advice.
    """
    turn_state = state.get("turn_state") or {}
    raw_query = turn_state.get("raw_query") or state.get("user_message") or ""
    
    # Check if query is simple thanks / bye
    q_lower = raw_query.strip().lower()
    if q_lower in ("thanks", "thank you", "thanks!", "thank you!"):
        reply = "You're welcome! Let me know if you need another outdoor activity safety check."
    elif q_lower in ("bye", "goodbye", "bye!", "good night"):
        reply = "Goodbye! Stay mindful of local conditions whenever you head outside."
    elif q_lower in ("ok", "okay", "cool", "ok cool", "okay cool"):
        reply = "Sounds good! Whenever you have an outdoor activity in mind, tell me the activity and place."
    else:
        # LLM response
        try:
            llm = llm_factory.get_llm(state.get("requested_model"))
            if llm:
                response = llm.invoke([
                    ("system", SMALLTALK_PROMPT),
                    ("human", raw_query)
                ])
                reply = response.content if hasattr(response, "content") else str(response)
                reply = reply.strip().strip('"\'')
            else:
                reply = FALLBACK_GREETING
        except Exception:
            reply = FALLBACK_GREETING

        # Output guards verification
        if (
            GUARD_DIGIT_UNIT.search(reply)
            or GUARD_WEATHER_WORDS.search(reply)
            or GUARD_ADVICE_WORDS.search(reply)
            or len(reply) > 280
        ):
            reply = FALLBACK_GREETING

    return {
        "final_response": reply,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.NO_HAZARD_MATCHED.value,
            "title": "Weabot Assistant · Casual Conversation",
            "severity": "low",
            "summary": "Casual conversation or greeting (non-weather)."
        },
        "weather_data": None,
        "effective_weather": None,
        "api_source": None
    }
