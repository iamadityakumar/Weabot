import asyncio
import json
import os
import sys
import uuid
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

# MB root in sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.graph import build_safety_graph, safety_advisor_graph
from backend.nodes.location import get_weather_client
from backend.nodes.weather import get_sops_engine
from backend.weather_client import WeatherClient, GeocodingError, WeatherAPIError
from backend.sops_engine import SOPsEngine
from backend.llm_factory import llm_factory
from langchain_core.messages import HumanMessage

BASE_URL = "http://127.0.0.1:8000"

async def call_api_chat(message: str, thread_id: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """Call the live running FastAPI /api/chat endpoint."""
    payload = {"message": message}
    if thread_id:
        payload["thread_id"] = thread_id
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{BASE_URL}/api/chat", json=payload)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {
                    "thread_id": thread_id or "error",
                    "response": f"HTTP {resp.status_code}: {resp.text}",
                    "sop_citations": [],
                    "weather_data": None,
                    "session_facts": None,
                    "error_message": resp.text,
                    "verdict": None,
                    "model_used": None,
                    "http_status": resp.status_code
                }
        except Exception as e:
            return {
                "thread_id": thread_id or "error",
                "response": f"Client exception: {str(e)}",
                "sop_citations": [],
                "weather_data": None,
                "session_facts": None,
                "error_message": str(e),
                "verdict": None,
                "model_used": None,
                "http_status": 500
            }

async def run_graph_with_mocks(
    message: str,
    mock_weather: Optional[Dict[str, Any]] = None,
    simulate_error: bool = False,
    mock_geocode: Optional[Dict[str, Any]] = None,
    mock_geocode_error: Optional[str] = None,
    session_facts: Optional[Dict[str, Any]] = None,
    thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute LangGraph directly with dependency injection for failure and mock tests."""
    weather_client = get_weather_client()
    graph = build_safety_graph(checkpointer=False)
    
    orig_fetch = weather_client.fetch_weather
    orig_geo = weather_client.geocode
    prev_sim = weather_client.simulate_unreachable

    if simulate_error:
        weather_client.simulate_unreachable = True

    if mock_weather is not None:
        async def _mock_fetch(*args, **kwargs):
            return mock_weather
        weather_client.fetch_weather = _mock_fetch

    if mock_geocode is not None:
        async def _mock_geo(*args, **kwargs):
            return mock_geocode
        weather_client.geocode = _mock_geo
    elif mock_geocode_error is not None:
        async def _mock_geo_err(*args, **kwargs):
            raise GeocodingError(mock_geocode_error)
        weather_client.geocode = _mock_geo_err

    try:
        input_state = {
            "messages": [HumanMessage(content=message)],
            "session_facts": session_facts or {}
        }
        res = await graph.ainvoke(input_state)
        return {
            "thread_id": thread_id or str(uuid.uuid4()),
            "response": res.get("final_response", ""),
            "sop_citations": res.get("sop_citations", []),
            "weather_data": res.get("weather_data"),
            "session_facts": res.get("session_facts"),
            "error_message": res.get("error_message"),
            "verdict": res.get("verdict"),
            "model_used": "Gemini / Safety Graph Engine"
        }
    finally:
        weather_client.fetch_weather = orig_fetch
        weather_client.geocode = orig_geo
        weather_client.simulate_unreachable = prev_sim

print("Helper functions defined successfully.")
