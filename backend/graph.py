from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.agent_state import AgentState
from backend.nodes.intake import intake_node
from backend.nodes.location import (
    ask_location_node,
    location_resolve_node,
    check_location_present,
    check_geocode_status,
    model_identity_node,
)
from backend.nodes.weather import fetch_weather_node, check_weather_status
from backend.nodes.matcher import match_sops_node, check_match_status
from backend.nodes.responder import no_match_node, failure_node, compose_node, out_of_scope_node
from backend.nodes.number_guard import validate_and_guard_numbers

def build_safety_graph(checkpointer: bool = True):
    """
    Constructs the LangGraph state machine with strict conditional branching,
    deterministic fallback nodes, and session checkpointing.
    """
    builder = StateGraph(AgentState)

    # Register Nodes
    builder.add_node("intake", intake_node)
    builder.add_node("out_of_scope", out_of_scope_node)
    builder.add_node("model_identity", model_identity_node)
    builder.add_node("ask_location", ask_location_node)
    builder.add_node("location_resolve", location_resolve_node)
    builder.add_node("fetch_weather", fetch_weather_node)
    builder.add_node("match_sops", match_sops_node)
    builder.add_node("compose", compose_node)
    builder.add_node("no_match", no_match_node)
    builder.add_node("number_guard", validate_and_guard_numbers)
    builder.add_node("failure", failure_node)

    # Entry point
    builder.add_edge(START, "intake")

    # Branch 1: Location present vs missing vs out_of_scope vs model_identity
    builder.add_conditional_edges(
        "intake",
        check_location_present,
        {
            "out_of_scope": "out_of_scope",
            "model_identity": "model_identity",
            "ask_location": "ask_location",
            "resolve_location": "location_resolve",
        },
    )

    # Out of scope, model identity, and missing location terminal paths
    builder.add_edge("out_of_scope", END)
    builder.add_edge("model_identity", END)
    builder.add_edge("ask_location", END)

    # Branch 2: Geocoding success vs error
    builder.add_conditional_edges(
        "location_resolve",
        check_geocode_status,
        {
            "failure": "failure",
            "fetch_weather": "fetch_weather",
        },
    )

    # Branch 3: Weather fetch success vs API error
    builder.add_conditional_edges(
        "fetch_weather",
        check_weather_status,
        {
            "failure": "failure",
            "match_sops": "match_sops",
        },
    )

    # Failure terminal path
    builder.add_edge("failure", END)

    # Branch 4: Rule matching (matches found vs no match)
    builder.add_conditional_edges(
        "match_sops",
        check_match_status,
        {
            "no_match": "no_match",
            "compose": "compose",
        },
    )

    # Runtime number guard validation before client emission
    builder.add_edge("compose", "number_guard")
    builder.add_edge("no_match", "number_guard")
    builder.add_edge("number_guard", END)

    if checkpointer:
        memory = MemorySaver()
        return builder.compile(checkpointer=memory)
    return builder.compile()

# Global pre-compiled graph instance with memory checkpointing
safety_advisor_graph = build_safety_graph(checkpointer=True)
