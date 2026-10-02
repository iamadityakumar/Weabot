from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.agent_state import AgentState
from backend.nodes.route import route_node
from backend.nodes.about_node import about_node
from backend.nodes.smalltalk_node import smalltalk_node
from backend.nodes.meta_node import meta_node
from backend.nodes.scope_node import scope_node
from backend.nodes.location_resolver import resolve_location_node
from backend.nodes.time_resolver_node import resolve_time_node
from backend.nodes.weather_fetch_node import fetch_weather_node
from backend.nodes.verify_payload_node import verify_payload_node
from backend.nodes.sop_selection_node import select_sops_node
from backend.nodes.sop_evaluation_node import evaluate_sops_node
from backend.nodes.precedence_node import resolve_precedence_node
from backend.nodes.render_node import render_node
from backend.nodes.guards_node import guards_node
from backend.nodes.decision_log_node import log_decision_node
from backend.nodes.failure_nodes import (
    location_fail_node,
    time_fail_node,
    data_fail_node,
)

# Conditional Edge Checkers
def check_location_branch(state: AgentState) -> str:
    turn_state = state.get("turn_state") or {}
    if turn_state.get("error_type") in ("location_fail", "ask_activity") or not turn_state.get("resolved_location"):
        return "location_fail"
    return "resolve_time"

def check_time_branch(state: AgentState) -> str:
    turn_state = state.get("turn_state") or {}
    if turn_state.get("error_type") == "time_fail":
        return "time_fail"
    return "fetch_weather"

def check_fetch_branch(state: AgentState) -> str:
    turn_state = state.get("turn_state") or {}
    if turn_state.get("error_type") == "data_fail" or not state.get("weather_data"):
        return "data_fail"
    return "verify_payload"

def check_verify_branch(state: AgentState) -> str:
    turn_state = state.get("turn_state") or {}
    if turn_state.get("error_type") == "data_fail":
        return "data_fail"
    return "select_sops"

def build_safety_graph(checkpointer: bool = True):
    """
    Target Graph with Router Gate Before Anything Else:
    START -> route ->
      - smalltalk: smalltalk_node -> END
      - about_bot: about_node -> END
      - meta_session: meta_node -> END
      - out_of_scope: scope_node -> END
      - weather_safety:
          resolve_location -> resolve_time -> fetch_weather -> verify_payload ->
          select_sops -> evaluate_sops -> resolve_precedence -> render -> guards -> log_decision
      failures: location_fail / time_fail / data_fail -> honest reply
    """
    builder = StateGraph(AgentState)

    # 1. Register All Nodes
    builder.add_node("route", route_node)
    builder.add_node("smalltalk_node", smalltalk_node)
    builder.add_node("about_node", about_node)
    builder.add_node("meta_node", meta_node)
    builder.add_node("scope_node", scope_node)
    
    # Weather path nodes
    builder.add_node("resolve_location", resolve_location_node)
    builder.add_node("resolve_time", resolve_time_node)
    builder.add_node("fetch_weather", fetch_weather_node)
    builder.add_node("verify_payload", verify_payload_node)
    builder.add_node("select_sops", select_sops_node)
    builder.add_node("evaluate_sops", evaluate_sops_node)
    builder.add_node("resolve_precedence", resolve_precedence_node)
    builder.add_node("render", render_node)
    builder.add_node("guards", guards_node)
    builder.add_node("log_decision", log_decision_node)

    # Failure nodes
    builder.add_node("location_fail", location_fail_node)
    builder.add_node("time_fail", time_fail_node)
    builder.add_node("data_fail", data_fail_node)

    # 2. Entry point: Router before anything else
    builder.add_edge(START, "route")

    # 3. Router Conditional Edges
    builder.add_conditional_edges(
        "route",
        lambda s: s.get("intent", "out_of_scope"),
        {
            "weather_safety": "resolve_location",
            "smalltalk": "smalltalk_node",
            "about_bot": "about_node",
            "meta_session": "meta_node",
            "out_of_scope": "scope_node"
        }
    )

    # Non-weather terminal paths (Zero weather data carried)
    builder.add_edge("smalltalk_node", END)
    builder.add_edge("about_node", END)
    builder.add_edge("meta_node", END)
    builder.add_edge("scope_node", END)

    # 4. Location branch (success vs location_fail / ask_activity)
    builder.add_conditional_edges(
        "resolve_location",
        check_location_branch,
        {
            "location_fail": "location_fail",
            "resolve_time": "resolve_time"
        }
    )
    builder.add_edge("location_fail", END)

    # 5. Time branch (success vs time_fail)
    builder.add_conditional_edges(
        "resolve_time",
        check_time_branch,
        {
            "time_fail": "time_fail",
            "fetch_weather": "fetch_weather"
        }
    )
    builder.add_edge("time_fail", END)

    # 6. Weather fetch branch (success vs data_fail)
    builder.add_conditional_edges(
        "fetch_weather",
        check_fetch_branch,
        {
            "data_fail": "data_fail",
            "verify_payload": "verify_payload"
        }
    )

    # 7. Payload verification branch (success vs data_fail)
    builder.add_conditional_edges(
        "verify_payload",
        check_verify_branch,
        {
            "data_fail": "data_fail",
            "select_sops": "select_sops"
        }
    )
    builder.add_edge("data_fail", END)

    # 8. Evaluation, Precedence, Render, Guards, Decision Log
    builder.add_edge("select_sops", "evaluate_sops")
    builder.add_edge("evaluate_sops", "resolve_precedence")
    builder.add_edge("resolve_precedence", "render")
    builder.add_edge("render", "guards")
    builder.add_edge("guards", "log_decision")
    builder.add_edge("log_decision", END)

    if checkpointer:
        memory = MemorySaver()
        return builder.compile(checkpointer=memory)
    return builder.compile()

# Default singleton instance with checkpointing enabled for FastAPI
safety_advisor_graph = build_safety_graph(checkpointer=True)
