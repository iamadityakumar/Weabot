from typing import Dict, Any, List
from backend.agent_state import AgentState, SafetyStatus
from backend.sops_engine import get_sops_engine

SEVERITY_WEIGHT = {
    "critical": 4,
    "high": 3,
    "moderate": 2,
    "low": 1
}

def resolve_precedence_node(state: AgentState) -> Dict[str, Any]:
    """
    Precedence Resolution Node:
    - Ranks universal overrides (e.g. SOP-001) first.
    - Sorts fired SOPs by severity: critical > high > moderate > low.
    - Determines SafetyStatus enum:
      - NO_POLICY if activity has no matching policy in the registry.
      - NO_HAZARD_MATCHED if policies exist/evaluated but thresholds not exceeded.
      - ADVISORY if moderate or low hazard SOP fires.
      - UNSAFE if high or critical hazard SOP fires.
    """
    turn_state = dict(state.get("turn_state") or {})
    fired_sops = list(state.get("fired_sops") or [])
    evaluated_sops = list(state.get("evaluated_sops") or [])
    activity = turn_state.get("activity") or "general outdoor activity"
    engine = get_sops_engine()

    # Sort fired SOPs: override first, then by severity weight descending
    def sort_key(sop: Dict[str, Any]):
        is_override = 1 if sop.get("override", False) else 0
        sev = SEVERITY_WEIGHT.get(sop.get("severity", "low"), 1)
        return (is_override, sev)

    fired_sops.sort(key=sort_key, reverse=True)

    # Universal override suppression: severe storm override (SOP-001) suppresses permissive leisure SOP-012
    if any(s.get("id") == "SOP-001" for s in fired_sops):
        fired_sops = [s for s in fired_sops if s.get("id") != "SOP-012"]

    # Check whether the activity itself is covered by any registered policy
    is_activity_covered = engine.has_specific_activity_sops(activity)

    # Determine status enum
    if fired_sops:
        top_sop = fired_sops[0]
        top_sev = top_sop.get("severity", "low")
        if top_sev in ("high", "critical") or top_sop.get("override", False):
            status = SafetyStatus.UNSAFE.value
            verdict_title = f"High Hazard Alert · {top_sop.get('title')}"
        else:
            status = SafetyStatus.ADVISORY.value
            verdict_title = f"Safety Advisory · {top_sop.get('title')}"
    elif is_activity_covered:
        status = SafetyStatus.NO_HAZARD_MATCHED.value
        top_sev = "low"
        verdict_title = "Advisory Checked · Below Alert Thresholds"
    else:
        status = SafetyStatus.NO_POLICY.value
        top_sev = "low"
        verdict_title = f"No Policy Defined · {activity.title()}"

    verdict = {
        "status": status,
        "title": verdict_title,
        "severity": top_sev,
        "summary": f"Evaluated {len(evaluated_sops)} SOPs, {len(fired_sops)} active hazard rules fired.",
        "activity": activity,
        "location": (turn_state.get("resolved_location") or {}).get("display", "Unknown")
    }

    citations = [s["id"] for s in fired_sops]

    return {
        "fired_sops": fired_sops,
        "matched_sops": fired_sops,
        "sop_citations": citations,
        "verdict": verdict,
        "turn_state": turn_state
    }
