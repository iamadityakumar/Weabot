from typing import Dict, Any
from backend.agent_state import AgentState, SafetyStatus

ABOUT = (
    "I'm Weabot, an outdoor-safety assistant. Tell me an activity and a place, "
    "and I'll check live weather against our approved safety guidelines. "
    "If no guideline covers it, I'll say so."
)

def about_node(state: AgentState) -> Dict[str, Any]:
    """
    Fix 3: About Bot Node
    Deterministic fixed text describing Weabot capabilities.
    Carries zero weather data and no card.
    """
    return {
        "final_response": ABOUT,
        "sop_citations": [],
        "verdict": {
            "status": SafetyStatus.NO_HAZARD_MATCHED.value,
            "title": "About Weabot · Outdoor Safety Advisor",
            "severity": "low",
            "summary": "Weabot outdoor-activity safety advisor capabilities."
        },
        "weather_data": None,
        "effective_weather": None,
        "api_source": None
    }
