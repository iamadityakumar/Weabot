from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class SessionFacts(TypedDict, total=False):
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    last_weather_snapshot: Optional[Dict[str, Any]]
    last_query_time: Optional[str]

class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    session_facts: SessionFacts
    extracted_intent: Optional[Dict[str, Any]]  # {activity: str, location: Optional[str], time_window: Optional[str]}
    weather_data: Optional[Dict[str, Any]]
    matched_sops: List[Dict[str, Any]]
    final_response: Optional[str]
    sop_citations: List[str]
    error_message: Optional[str]
