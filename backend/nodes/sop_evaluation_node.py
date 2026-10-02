from typing import Dict, Any, List
from backend.agent_state import AgentState
from backend.sops_engine import get_sops_engine

def evaluate_sops_node(state: AgentState) -> Dict[str, Any]:
    """
    WP5 Deterministic SOP Evaluation Node (Pure Python):
    1. Universal overrides (SOP-001 severe rain, SOP-006 gale, SOP-002 extreme heat)
       are evaluated BEFORE activity eligibility, for every activity including uncovered ones.
    2. Evaluates selected candidate SOPs deterministically in Python against target time weather metrics.
    3. Identifies evaluated SOPs and fired SOPs.
    """
    turn_state = dict(state.get("turn_state") or {})
    weather = state.get("effective_weather") or state.get("weather_data") or {}
    selected_sop_ids = state.get("selected_sop_ids") or []
    activity = turn_state.get("activity") or "general outdoor activity"
    engine = get_sops_engine()

    evaluated_sops = []
    fired_sops = []

    # 1. Universal Overrides evaluation (evaluated for every activity, even uncovered ones)
    universal_override_ids = ["SOP-001", "SOP-002", "SOP-006"]
    for uid in universal_override_ids:
        if uid in engine.sops:
            sop = engine.sops[uid]
            if sop not in evaluated_sops:
                evaluated_sops.append(sop)
            # Evaluate conditions deterministically
            all_met = True
            for cond in sop.get("conditions", []):
                if not engine.evaluate_condition(cond, weather):
                    all_met = False
                    break
            if all_met:
                if sop not in fired_sops:
                    fired_sops.append(sop)

    # 2. Activity / Candidate SOPs evaluation
    for cid in selected_sop_ids:
        if cid in engine.sops:
            sop = engine.sops[cid]
            if sop not in evaluated_sops:
                evaluated_sops.append(sop)
            
            # Check if condition fires
            all_met = True
            for cond in sop.get("conditions", []):
                if not engine.evaluate_condition(cond, weather):
                    all_met = False
                    break
            if all_met:
                if sop not in fired_sops:
                    fired_sops.append(sop)

    return {
        "evaluated_sops": evaluated_sops,
        "fired_sops": fired_sops,
        "matched_sops": fired_sops,  # For backward compatibility
        "turn_state": turn_state
    }
