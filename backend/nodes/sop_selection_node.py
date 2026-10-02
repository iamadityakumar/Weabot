import json
import re
from typing import Dict, Any, List
from backend.agent_state import AgentState
from backend.sops_engine import get_sops_engine
from backend.llm_factory import llm_factory

def select_sops_node(state: AgentState) -> Dict[str, Any]:
    """
    WP5 SOP Selection Node:
    - LLM selection at temperature 0 using a catalog of ID, title, and intent ONLY (no thresholds).
    - Drops any ID not in registry.
    - Adds vulnerable-group matching SOPs (child -> SOP-008/013, elderly -> SOP-007, pet -> SOP-009).
    - Guarantees universal overrides (SOP-001, SOP-006, SOP-002) are candidate for evaluation.
    """
    turn_state = dict(state.get("turn_state") or {})
    query = turn_state.get("raw_query", "")
    activity = turn_state.get("activity", "general outdoor activity")
    subject = turn_state.get("subject", "adult")

    engine = get_sops_engine()
    registry = engine.sops

    # Build catalog of ID, Title, Intent ONLY
    catalog = []
    for sop_id, sop in registry.items():
        catalog.append({
            "id": sop_id,
            "title": sop.get("title", ""),
            "intent": sop.get("intent", sop.get("title", ""))
        })

    candidate_ids = set()

    # Rule-based / demographic candidate inclusion
    if subject == "child":
        candidate_ids.update(["SOP-008", "SOP-013"])
    elif subject == "elderly":
        candidate_ids.update(["SOP-007", "SOP-002", "SOP-003"])
    elif subject == "pet":
        candidate_ids.update(["SOP-009"])

    # Fast path keyword & alias mapping
    act_lower = (activity or "").lower()
    q_lower = query.lower()

    if any(k in act_lower or k in q_lower for k in ["scooter", "motorcycle", "motorbike", "moped", "two-wheeler"]):
        candidate_ids.update(["SOP-004"])  # Wind handling, excludes athletic workout SOP-003
    elif any(k in act_lower or k in q_lower for k in ["cycl", "bike", "bicycle", "pedal", "two wheels", "two-wheel", "two wheeler"]):
        candidate_ids.update(["SOP-004", "SOP-003"])
    if any(k in act_lower or k in q_lower for k in ["run", "jog", "exercise", "workout"]):
        candidate_ids.update(["SOP-002", "SOP-003"])
    if not any(u in q_lower or u in act_lower for u in ["drone", "uav", "camera"]) and any(k in act_lower or k in q_lower for k in ["picnic", "park", "bbq", "barbecue", "gathering"]):
        candidate_ids.update(["SOP-011", "SOP-012"])
    if any(k in act_lower or k in q_lower for k in ["drive", "commute", "car", "travel", "road"]):
        candidate_ids.update(["SOP-005", "SOP-006"])
    if any(k in q_lower for k in ["thunder", "lightning", "storm"]):
        candidate_ids.update(["SOP-010"])
    # Dynamic candidate selection based on SOP applies_to
    for sop_id, sop in registry.items():
        applies = [str(x).lower().strip() for x in sop.get("applies_to", [])]
        if any(target in act_lower or act_lower in target for target in applies if target not in ("all", "any")):
            candidate_ids.add(sop_id)
        if any(target in q_lower for target in applies if len(target) >= 4 and target not in ("all", "any")):
            candidate_ids.add(sop_id)

    # LLM Candidate Selection step (temperature 0)
    llm_candidates = llm_factory.select_sop_candidates(query, activity, subject, catalog, model_name=state.get("requested_model"))
    for cid in llm_candidates:
        if cid in registry:
            candidate_ids.add(cid)

    # Ensure drone/UAV queries discard picnic/park leisure gathering SOPs
    if any(u in q_lower or u in act_lower for u in ["drone", "uav"]):
        candidate_ids.discard("SOP-011")
        candidate_ids.discard("SOP-012")

    # Universal overrides (SOP-001 severe rain, SOP-006 gale/fog, SOP-002 extreme heat)
    # are ALWAYS candidates so evaluate_sops can test override triggers
    candidate_ids.add("SOP-001")
    candidate_ids.add("SOP-002")
    candidate_ids.add("SOP-006")

    # Exclude pet-specific protocol SOP-009 if subject is not a pet
    if subject != "pet":
        candidate_ids.discard("SOP-009")

    # Drop any ID not in registry
    valid_candidates = sorted([cid for cid in candidate_ids if cid in registry])

    return {
        "selected_sop_ids": valid_candidates,
        "turn_state": turn_state
    }
