from enum import Enum
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class SafetyStatus(str, Enum):
    NO_POLICY = "NO_POLICY"
    NO_HAZARD_MATCHED = "NO_HAZARD_MATCHED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    REFUSED = "REFUSED"
    ADVISORY = "ADVISORY"
    UNSAFE = "UNSAFE"

class TurnState(TypedDict, total=False):
    """
    State rebuilt from scratch every turn (intent, activity, subject, time expression).
    Fixes stale flags (#18, #24, #26, #28, #32).
    """
    raw_query: str
    dialogue_act: str  # new_query, time_shift, activity_shift, challenge, override_attempt, fake_policy, summary, disclosure, out_of_scope
    raw_location: Optional[str]
    resolved_location: Optional[Dict[str, Any]]
    activity: Optional[str]
    activity_label: Optional[str]  # Gerund form (e.g. "cycling", "walking", "outdoor gathering")
    subject: Optional[str]  # "child", "elderly", "pet", "adult"
    time_expression: Optional[str]
    time_target: Optional[Dict[str, Any]]  # {kind, iso, assumed, target_hour, target_date, display_target}
    is_followup: bool
    fake_sop_id: Optional[str]
    challenge_context: Optional[str]
    error_type: Optional[str]  # location_fail, time_fail, data_fail
    error_message: Optional[str]

class SessionState(TypedDict, total=False):
    """
    Longer-lived session state holding only validated context:
    - last_good_location (a failed geocode must never write here)
    - decision_log
    - last_activity
    - last_subject
    """
    last_good_location: Optional[Dict[str, Any]]
    last_activity: Optional[str]
    last_subject: Optional[str]
    decision_log: List[Dict[str, Any]]

# Legacy SessionFacts for backward compatibility with frontend and evaluation helpers
class SessionFacts(TypedDict, total=False):
    location_name: Optional[str]
    location_display: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    activity: Optional[str]
    subject: Optional[str]
    last_weather_snapshot: Optional[Dict[str, Any]]
    last_query_time: Optional[str]
    last_verdict_title: Optional[str]

class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_message: Optional[str]
    intent: Optional[str]  # weather_safety, smalltalk, about_bot, meta_session, out_of_scope
    place_text: Optional[str]
    activity_text: Optional[str]
    turn_state: TurnState
    session_state: SessionState
    
    # Multi-turn clarification & pending request state
    pending_request: Optional[Dict[str, Any]]
    awaiting_slot: Optional[str]
    location: Optional[str]
    activity: Optional[str]
    route: Optional[str]
    just_resolved_pending_slot: Optional[bool]

    # Target graph intermediate state
    weather_data: Optional[Dict[str, Any]]
    effective_weather: Optional[Dict[str, Any]]
    selected_sop_ids: List[str]
    evaluated_sops: List[Dict[str, Any]]
    fired_sops: List[Dict[str, Any]]
    verdict: Optional[Dict[str, Any]]
    final_response: Optional[str]
    sop_citations: List[str]
    requested_model: Optional[str]
    model_used: Optional[str]
    quota_exhausted: Optional[bool]
    exhausted_model: Optional[str]
    fallback_model: Optional[str]
    fallback_notice: Optional[str]
    api_source: Optional[Dict[str, Any]]
    
    # Backward compatibility slots
    session_facts: SessionFacts
    extracted_intent: Optional[Dict[str, Any]]
    matched_sops: List[Dict[str, Any]]
    unverified_sops: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    error_type: Optional[str]
    unknown_location_name: Optional[str]

canonical_activity_ids = {
    "cycling", "skydiving", "scootering", "riding a motorbike", "riding a motorcycle",
    "running", "jogging", "walking", "driving", "commuting", "outdoor gathering",
    "outdoor play", "park outing", "flying a drone", "swimming", "hiking",
    "mountain climbing", "indoor yoga", "general outdoor activity",
    "surfing", "kayaking", "bungee jumping"
}

def assert_pending_request_consistency(state: Dict[str, Any]):
    """
    Validates state integrity invariants for pending clarification requests.
    Prevents ungrounded weather calls without verified parameters.
    """
    pending = state.get("pending_request")
    if not pending:
        return
    if state.get("awaiting_slot") == "location":
        assert pending.get("location") is None, f"Expected pending location to be None, got {pending.get('location')}"
    if pending.get("location"):
        assert pending["location"] != "", "Pending location cannot be empty string"
    if pending.get("activity"):
        assert pending["activity"] in canonical_activity_ids, f"Pending activity '{pending['activity']}' not in canonical_activity_ids"

    # Strongest invariant: for any request that has entered weather_safety
    route_name = state.get("route") or state.get("intent")
    if route_name in ("weather_safety", "WEATHER_SAFETY_READY", "resume_weather_safety"):
        loc = state.get("location") or (state.get("turn_state") and state.get("turn_state").get("resolved_location")) or (pending and pending.get("location"))
        assert not (
            state.get("awaiting_slot") is None
            and not loc
        ), f"Invariant violated: request entered weather_safety with awaiting_slot=None but no location in state: {state}"

