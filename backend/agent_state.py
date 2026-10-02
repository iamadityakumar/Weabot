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
    turn_state: TurnState
    session_state: SessionState
    
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
    api_source: Optional[Dict[str, Any]]
    
    # Backward compatibility slots
    session_facts: SessionFacts
    extracted_intent: Optional[Dict[str, Any]]
    matched_sops: List[Dict[str, Any]]
    unverified_sops: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    error_type: Optional[str]
    unknown_location_name: Optional[str]
