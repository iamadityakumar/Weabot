import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
import asyncio
import uuid
import re
import difflib
from typing import Dict, Any
from langchain_core.messages import HumanMessage

from backend.graph import build_safety_graph
from backend.nodes.location import get_weather_client
from backend.agent_state import SafetyStatus
from backend.nodes.about_node import ABOUT
from backend.nodes.scope_node import SCOPE_TEXT
from backend.nodes.location_resolver import STOP, sim

@pytest.fixture(scope="module")
def graph_instance():
    wc = get_weather_client()
    wc.use_city_stubs = True
    return build_safety_graph(checkpointer=True)

@pytest.mark.asyncio
async def test_greetings_friendly_reply_no_card_no_data(graph_instance):
    """Hey, hi, Hello!, yo, namaste -> A friendly reply with no card, no place and no data"""
    greetings = ["Hey", "hi", "Hello!", "yo", "namaste"]
    for greet in greetings:
        cfg = {"configurable": {"thread_id": f"test-greet-{uuid.uuid4()}"}}
        res = await graph_instance.ainvoke({"messages": [HumanMessage(content=greet)], "user_message": greet}, config=cfg)
        resp = res.get("final_response", "")
        
        # Must have text reply
        assert len(resp) > 0, f"Greeting '{greet}' gave empty reply"
        # Zero weather data
        assert res.get("weather_data") is None, f"Greeting '{greet}' leaked weather_data"
        assert res.get("effective_weather") is None, f"Greeting '{greet}' leaked effective_weather"
        # Zero place
        assert (res.get("turn_state") or {}).get("resolved_location") is None, f"Greeting '{greet}' resolved location"
        # Intent must be smalltalk
        assert (res.get("turn_state") or {}).get("dialogue_act") == "smalltalk" or res.get("intent") == "smalltalk"

@pytest.mark.asyncio
async def test_short_natural_replies(graph_instance):
    """thanks, ok cool, bye -> A short natural reply"""
    queries = ["thanks", "ok cool", "bye"]
    for q in queries:
        cfg = {"configurable": {"thread_id": f"test-short-{uuid.uuid4()}"}}
        res = await graph_instance.ainvoke({"messages": [HumanMessage(content=q)], "user_message": q}, config=cfg)
        resp = res.get("final_response", "")
        
        assert len(resp) > 0
        assert res.get("weather_data") is None
        assert (res.get("turn_state") or {}).get("resolved_location") is None

@pytest.mark.asyncio
async def test_how_are_you(graph_instance):
    """how are you? -> A short natural reply"""
    cfg = {"configurable": {"thread_id": f"test-howareyou-{uuid.uuid4()}"}}
    res = await graph_instance.ainvoke({"messages": [HumanMessage(content="how are you?")], "user_message": "how are you?"}, config=cfg)
    resp = res.get("final_response", "")
    
    assert len(resp) > 0
    assert res.get("weather_data") is None
    assert (res.get("turn_state") or {}).get("resolved_location") is None

@pytest.mark.asyncio
async def test_about_bot(graph_instance):
    """who are you?, what can you do? -> The About text"""
    for q in ["who are you?", "what can you do?"]:
        cfg = {"configurable": {"thread_id": f"test-about-{uuid.uuid4()}"}}
        res = await graph_instance.ainvoke({"messages": [HumanMessage(content=q)], "user_message": q}, config=cfg)
        resp = res.get("final_response", "")
        
        assert ABOUT in resp or "Weabot, an outdoor-safety assistant" in resp
        assert res.get("weather_data") is None
        assert (res.get("turn_state") or {}).get("resolved_location") is None

@pytest.mark.asyncio
async def test_scope_reply(graph_instance):
    """tell me a joke, write a python function, best pizza in Delhi, Tesla stock? -> The Weabot scope reply"""
    queries = ["tell me a joke", "write a python function", "best pizza in Delhi", "Tesla stock?"]
    for q in queries:
        cfg = {"configurable": {"thread_id": f"test-scope-{uuid.uuid4()}"}}
        res = await graph_instance.ainvoke({"messages": [HumanMessage(content=q)], "user_message": q}, config=cfg)
        resp = res.get("final_response", "")
        verdict = res.get("verdict") or {}
        
        assert verdict.get("status") == SafetyStatus.OUT_OF_SCOPE.value
        assert "outside" in resp.lower() or "scope" in resp.lower() or "can't help" in resp.lower()
        assert res.get("weather_data") is None

@pytest.mark.asyncio
async def test_greeting_plus_real_question(graph_instance):
    """Hey, is it safe to cycle in Bhopal? -> The weather path (greeting plus a real question)"""
    cfg = {"configurable": {"thread_id": f"test-real-{uuid.uuid4()}"}}
    q = "Hey, is it safe to cycle in Bhopal?"
    res = await graph_instance.ainvoke({"messages": [HumanMessage(content=q)], "user_message": q}, config=cfg)
    resp = res.get("final_response", "")
    
    assert "bhopal" in resp.lower()
    assert res.get("weather_data") is not None
    assert res.get("verdict") is not None
    assert res.get("verdict", {}).get("status") in ("ADVISORY", "NO_HAZARD_MATCHED")

@pytest.mark.asyncio
async def test_bhopal_alone_asks_activity(graph_instance):
    """Bhopal alone -> One question: 'what activity?'"""
    cfg = {"configurable": {"thread_id": f"test-bhopal-alone-{uuid.uuid4()}"}}
    q = "Bhopal"
    res = await graph_instance.ainvoke({"messages": [HumanMessage(content=q)], "user_message": q}, config=cfg)
    resp = res.get("final_response", "")
    
    assert "activity" in resp.lower()
    assert "bhopal" in resp.lower()
    # Must NOT render a weather card
    assert res.get("weather_data") is None

@pytest.mark.asyncio
async def test_hey_bhopal_asks_activity(graph_instance):
    """hey bhopal -> Weather path only if the router extracts a place, and it asks for the activity"""
    cfg = {"configurable": {"thread_id": f"test-hey-bhopal-{uuid.uuid4()}"}}
    q = "hey bhopal"
    res = await graph_instance.ainvoke({"messages": [HumanMessage(content=q)], "user_message": q}, config=cfg)
    resp = res.get("final_response", "")
    
    assert "activity" in resp.lower()
    assert "bhopal" in resp.lower()
    assert res.get("weather_data") is None

@pytest.mark.asyncio
async def test_hello_as_geocoded_string_rejected():
    """Hello as a geocoded string -> Never resolves to a place"""
    assert "hello" in STOP
    assert "hey" in STOP
    assert "hi" in STOP
    
    # Similarity ratio between "Hello" and any random town like "Heijplaat" is < 0.8
    assert sim("Hello", "Heijplaat") < 0.8
    assert sim("Hello", "Hell-Ville") < 0.8

@pytest.mark.asyncio
async def test_router_llm_error_injected(graph_instance, monkeypatch):
    """Router LLM error injected -> The scope reply, never a weather card"""
    from backend.llm_factory import llm_factory
    
    class BrokenLLM:
        def with_structured_output(self, *args, **kwargs):
            class BrokenOutput:
                def invoke(self, *a, **kw):
                    raise RuntimeError("Simulated router LLM failure")
            return BrokenOutput()

    monkeypatch.setattr(llm_factory, "get_llm", lambda *a, **kw: BrokenLLM())
    
    cfg = {"configurable": {"thread_id": f"test-error-inj-{uuid.uuid4()}"}}
    q = "Can I do a marathon in Aurangabad next Tuesday?"
    res = await graph_instance.ainvoke({"messages": [HumanMessage(content=q)], "user_message": q}, config=cfg)
    
    # Fail-closed guarantee: out_of_scope reply, never weather card
    assert res.get("verdict", {}).get("status") == SafetyStatus.OUT_OF_SCOPE.value
    assert res.get("weather_data") is None

@pytest.mark.asyncio
async def test_geocoder_unrelated_top_hit_rejected():
    """Geocoder returns an unrelated top hit -> Rejected by the similarity check"""
    q = "RandomGibberishCityName"
    hit_name = "Randers"
    ratio = sim(q, hit_name)
    assert ratio < 0.8, f"Expected similarity ratio < 0.8, got {ratio}"
