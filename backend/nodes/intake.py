from typing import Dict, Any
from backend.agent_state import AgentState
from backend.llm_factory import llm_factory

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

    session_facts = state.get("session_facts", {})
    intent = llm_factory.extract_intent(user_text, session_facts)

    # If location is still not found in query, check if session_facts has a previously resolved location
    if not intent.get("location") and session_facts.get("location_name"):
        intent["location"] = session_facts["location_name"]

    return {
        "extracted_intent": intent
    }
