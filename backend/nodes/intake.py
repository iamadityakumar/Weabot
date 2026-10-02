from typing import Dict, Any
from backend.agent_state import AgentState
from backend.llm_factory import llm_factory, clean_and_validate_location

def intake_node(state: AgentState) -> Dict[str, Any]:
    """
    Intake node:
    - Extracts activity, location, and time_window from user message.
    - Preserves and merges context with existing session_facts for follow-up questions.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"extracted_intent": {"activity": "outdoor activity", "location": None, "time_window": "current"}}

    # Get latest message
    latest_msg = messages[-1]
    user_text = latest_msg.content if hasattr(latest_msg, "content") else str(latest_msg)

    session_facts = dict(state.get("session_facts") or {})
    requested_model = state.get("requested_model")
    intent = llm_factory.extract_intent(user_text, session_facts, model_name=requested_model)

    # Sanitize extracted location candidate
    valid_loc = clean_and_validate_location(intent.get("location"))
    if not valid_loc and session_facts.get("location_name"):
        # If user explicitly asked "here" without context, do not silently default
        if not any(k in user_text.lower() for k in ["what's it like here", "what is it like here", "weather here"]):
            valid_loc = clean_and_validate_location(session_facts["location_name"])
    intent["location"] = valid_loc

    # Preserve and carry forward activity across turns
    extracted_act = intent.get("activity")
    if extracted_act and extracted_act not in ("outdoor activity", "none", "this outdoor activity", "all", "any", "outdoor"):
        session_facts["activity"] = extracted_act
    elif session_facts.get("activity"):
        intent["activity"] = session_facts["activity"]

    return {
        "extracted_intent": intent,
        "session_facts": session_facts
    }

