from backend.agent_state import AgentState

def route_turn(state: AgentState) -> str:
    """
    Router according to Target Graph:
    parse_turn -> route ->
      meta_node (challenge / override / fake SOP / summary / disclosure)
      scope_node (out of scope)
      weather path: resolve_location
    """
    turn_state = state.get("turn_state") or {}
    act = turn_state.get("dialogue_act", "new_query")

    if act in ("challenge", "override_attempt", "fake_policy", "summary", "disclosure", "model_identity"):
        return "meta_node"

    if act == "out_of_scope":
        return "scope_node"

    # All regular inquiries, time shifts, and activity shifts enter weather path
    return "resolve_location"
