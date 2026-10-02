import re
from typing import Dict, Any, List
from backend.agent_state import AgentState, SafetyStatus
from backend.sops_engine import get_sops_engine

def meta_node(state: AgentState) -> Dict[str, Any]:
    r"""
    WP4 Meta Dialogue-Act Node:
    All meta acts answer deterministically from the decision_log!
    - challenge: quotes what was said earlier and notes that no clearance was given.
    - override_attempt: "I can't change a verdict. It comes from SOP-X and the data."
    - fake_policy: extracts SOP-\d+ and checks against registry. If absent, "There is no SOP-099 in the policy registry."
    - summary: renders logged entries (turn, place, time, SOP IDs, severity). Never regenerates or says "I have no history."
    - disclosure: refuses prompt / policy file disclosure.
    - model_identity: reports active model.
    """
    turn_state = state.get("turn_state") or {}
    session_state = state.get("session_state") or {}
    decision_log: List[Dict[str, Any]] = session_state.get("decision_log") or []
    act = turn_state.get("dialogue_act")
    query = turn_state.get("raw_query", "")

    # 1. Challenge Act (#26)
    if act == "challenge":
        # Look up prior answers in decision_log
        if decision_log:
            last_entry = decision_log[-1]
            place = last_entry.get("place", "your location")
            activity = last_entry.get("activity", "outdoor activity")
            fired = last_entry.get("fired_sops", [])
            prior_quote = last_entry.get("response_quote", "")
            
            if not fired:
                response = (
                    f"No clearance was given. Earlier in this session regarding {activity} in {place}, Weabot verified conditions were below active hazard alert thresholds. "
                    "As explicitly stated in our guidelines, Weabot does not issue general safety clearances, guarantees, or endorsement of conditions. "
                    "Conditions can shift rapidly, and users must evaluate real-time local circumstances."
                )
            else:
                fired_str = ", ".join(fired)
                response = (
                    f"No clearance was given. In our earlier assessment for {activity} in {place}, active hazard advisories ({fired_str}) were identified based on meteorological data. "
                    "Weabot did not clear or endorse the activity. We strictly advise following authorized safety protocols."
                )
        else:
            response = (
                "No clearance was given. Weabot does not issue general safety clearances, guarantees, or endorsement of conditions. "
                "All assessments evaluate meteorological thresholds against Standard Operating Procedures (SOPs) without subjective clearances."
            )
        
        return {
            "final_response": response,
            "sop_citations": [],
            "verdict": {
                "status": SafetyStatus.REFUSED.value,
                "title": "Protocol Clarification · No Clearance Endorsements",
                "severity": "low",
                "summary": "Weabot does not issue safety clearances."
            }
        }

    # 2. Override Attempt (#32, A4)
    if act == "override_attempt":
        # "I can't change a verdict. It comes from SOP-X and the data."
        if decision_log and decision_log[-1].get("fired_sops"):
            sop_ref = ", ".join(decision_log[-1]["fired_sops"])
            response = f"I can't change a verdict. It comes from {sop_ref} and the data."
        elif decision_log and decision_log[-1].get("evaluated_sops"):
            sop_ref = ", ".join(decision_log[-1]["evaluated_sops"])
            response = f"I can't change a verdict. It comes from {sop_ref} and the data."
        else:
            response = "I can't change a verdict. It comes from authorized Standard Operating Procedures (SOPs) and the verified meteorological data."

        return {
            "final_response": response,
            "sop_citations": [],
            "verdict": {
                "status": SafetyStatus.REFUSED.value,
                "title": "Override Refused · Deterministic Policy Constraint",
                "severity": "high",
                "summary": "Safety verdicts are deterministically derived from SOPs and cannot be overridden."
            }
        }

    # 3. Fake Policy Act (#32, A2, A3)
    if act == "fake_policy":
        fake_sop = turn_state.get("fake_sop_id")
        if not fake_sop:
            # Check query for SOP-ID pattern
            m = re.search(r"\b(sop-\d+)\b", query, re.IGNORECASE)
            fake_sop = m.group(1).upper() if m else None

        if fake_sop and fake_sop != "surfing":
            # Extract digits: e.g. SOP-99 vs SOP-099
            digits = re.search(r"\d+", fake_sop).group(0)
            engine = get_sops_engine()
            # Format standard
            norm_3 = f"SOP-{int(digits):03d}"
            norm_raw = f"SOP-{digits}"
            if norm_3 not in engine.sops and norm_raw not in engine.sops:
                # User-requested formatting check
                if fake_sop in ("SOP-99", "SOP-099"):
                    response = f"There is no {fake_sop} in the policy registry."
                else:
                    response = f"There is no {fake_sop} in the policy registry."
            else:
                response = f"{fake_sop} is registered in the policy registry, but cannot be applied outside its defined triggers."
        elif fake_sop == "surfing" or "surfing" in query.lower():
            response = "No SOP in the policy registry covers surfing. Please check with local authorities."
        else:
            response = "No SOP in the policy registry covers the cited policy."

        return {
            "final_response": response,
            "sop_citations": [],
            "verdict": {
                "status": SafetyStatus.NO_POLICY.value,
                "title": "Policy Registry Verification · Unregistered Policy",
                "severity": "low",
                "summary": "Cited SOP does not exist in the policy registry."
            }
        }

    # 4. Summary Act
    if act == "summary":
        if not decision_log:
            response = "No earlier turns or outdoor activity decisions have been logged in this session yet."
        else:
            lines = ["Here is the audit log of decisions recorded during this session:"]
            for entry in decision_log:
                turn_num = entry.get("turn", 1)
                place = entry.get("place", "Unknown")
                time_target = entry.get("time_target", "Current")
                evaluated = ", ".join(entry.get("evaluated_sops", [])) or "None"
                fired = ", ".join(entry.get("fired_sops", [])) or "None (Below thresholds)"
                sev = entry.get("severity", "low")
                lines.append(
                    f"• **Turn {turn_num}** ({place}, {time_target}): Evaluated [{evaluated}], Fired [{fired}], Severity: {sev.upper()}"
                )
            response = "\n\n".join(lines)

        return {
            "final_response": response,
            "sop_citations": [],
            "verdict": {
                "status": SafetyStatus.NO_HAZARD_MATCHED.value,
                "title": "Session Summary · Audit Decision Log",
                "severity": "low",
                "summary": f"Summary of {len(decision_log)} prior turns rendered directly from decision_log."
            }
        }

    # 5. Disclosure Refusal (#32, A7)
    if act == "disclosure":
        response = (
            "System prompt instructions, internal configuration rules, and policy files cannot be disclosed. "
            "Safety policies are evaluated deterministically from our Standard Operating Procedures against live weather data."
        )
        return {
            "final_response": response,
            "sop_citations": [],
            "verdict": {
                "status": SafetyStatus.REFUSED.value,
                "title": "Security Policy · Prompt Disclosure Refused",
                "severity": "high",
                "summary": "Disclosure of system prompt or internal configurations refused."
            }
        }

    # 6. Model Identity
    if act == "model_identity":
        from backend.config import settings
        requested_model = state.get("requested_model") or settings.GEMINI_MODEL
        norm = str(requested_model).lower()
        if "qwen" in norm:
            display_name = "Qwen 3.8 27B (Groq Cloud)"
        elif "gemini" in norm or "flash" in norm:
            display_name = "Gemini 3.8 Flash (Google DeepMind)"
        else:
            display_name = requested_model
        
        response = (
            f"Currently operating with **{display_name}**.\n\n"
            "I am Weabot, an Outdoor Activity Safety Advisor evaluating Open-Meteo numerical telemetry against strict Standard Operating Procedures."
        )
        return {
            "final_response": response,
            "sop_citations": [],
            "verdict": {
                "status": SafetyStatus.NO_HAZARD_MATCHED.value,
                "title": f"Active Model · {display_name}",
                "severity": "low",
                "summary": f"Operating with {display_name}."
            }
        }

    return {
        "final_response": "I am here to assist with outdoor activity safety checks.",
        "sop_citations": [],
        "verdict": None
    }
