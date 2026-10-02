import asyncio
import sys
from pathlib import Path
from langchain_core.messages import HumanMessage

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.graph import build_safety_graph
from backend.nodes.weather import get_sops_engine

async def run_test():
    print("=" * 60)
    print("RUNNING T-UNC: Universal Override on Uncovered Activities Suite")
    print("=" * 60)

    engine = get_sops_engine()
    engine.reload()
    graph = build_safety_graph(checkpointer=False)

    severe_weather = {
        "current": {
            "temperature_2m": 24.5,
            "apparent_temperature": 27.0,
            "precipitation": 22.0,
            "precipitation_probability": 95,
            "rain": 20.0,
            "wind_speed_10m": 42.0,
            "wind_gusts_10m": 68.0,
            "uv_index": 1.0,
            "weather_code": 65,
            "relative_humidity_2m": 92,
            "is_day": 1
        }
    }

    calm_weather = {
        "current": {
            "temperature_2m": 22.0,
            "apparent_temperature": 22.5,
            "precipitation": 0.0,
            "precipitation_probability": 5,
            "rain": 0.0,
            "wind_speed_10m": 8.0,
            "wind_gusts_10m": 12.0,
            "uv_index": 3.0,
            "weather_code": 0,
            "relative_humidity_2m": 50,
            "is_day": 1
        }
    }

    # Test 1: Uncovered activity (swimming) under SEVERE RAIN must trigger SOP-001
    print("\n[T-UNC-1] Evaluating swimming under severe storm...")
    res_swim_severe = await graph.ainvoke({
        "messages": [HumanMessage(content="Is it safe to go for a river swim in Bhopal?")],
        "weather_data": severe_weather,
        "session_facts": {"location_name": "Bhopal", "primary_location": "Bhopal"}
    })
    cites1 = res_swim_severe.get("sop_citations", [])
    verdict1 = res_swim_severe.get("verdict", {})
    print(f"Citations: {cites1}")
    print(f"Verdict Status: {verdict1.get('status')}, Title: {verdict1.get('title')}")
    assert "SOP-001" in cites1, f"Expected SOP-001 override to fire for swimming, got {cites1}"
    assert verdict1.get("status") == "UNSAFE", f"Expected UNSAFE, got {verdict1.get('status')}"
    print("PASS: Severe override evaluates BEFORE activity check and fires for swimming.")

    # Test 2: Uncovered activity (drone) under SEVERE RAIN must trigger SOP-001
    print("\n[T-UNC-2] Evaluating drone flight under severe storm...")
    res_drone_severe = await graph.ainvoke({
        "messages": [HumanMessage(content="Can I fly my drone in Bhopal today?")],
        "weather_data": severe_weather,
        "session_facts": {"location_name": "Bhopal", "primary_location": "Bhopal"}
    })
    cites2 = res_drone_severe.get("sop_citations", [])
    verdict2 = res_drone_severe.get("verdict", {})
    assert "SOP-001" in cites2, f"Expected SOP-001 override to fire for drone, got {cites2}"
    assert verdict2.get("status") == "UNSAFE"
    print("PASS: Severe override fires for drone.")

    # Test 3: Uncovered activity (generic 'go out') under SEVERE RAIN must trigger SOP-001
    print("\n[T-UNC-3] Evaluating generic 'go out' under severe storm...")
    res_go_severe = await graph.ainvoke({
        "messages": [HumanMessage(content="Can I go out in Bhopal today?")],
        "weather_data": severe_weather,
        "session_facts": {"location_name": "Bhopal", "primary_location": "Bhopal"}
    })
    cites3 = res_go_severe.get("sop_citations", [])
    verdict3 = res_go_severe.get("verdict", {})
    assert "SOP-001" in cites3, f"Expected SOP-001 override for 'go out', got {cites3}"
    assert verdict3.get("status") == "UNSAFE"
    print("PASS: Severe override fires for generic outdoor activity ('go out').")

    # Test 4: Uncovered activity (swimming) under CALM weather must return NO_POLICY (honest refusal)
    print("\n[T-UNC-4] Evaluating swimming under calm weather...")
    res_swim_calm = await graph.ainvoke({
        "messages": [HumanMessage(content="Can I go for a swim in Bhopal?")],
        "weather_data": calm_weather,
        "session_facts": {"location_name": "Bhopal", "primary_location": "Bhopal"}
    })
    cites4 = res_swim_calm.get("sop_citations", [])
    verdict4 = res_swim_calm.get("verdict", {})
    resp4 = res_swim_calm.get("final_response", "")
    print(f"Verdict Status: {verdict4.get('status')}, Title: {verdict4.get('title')}")
    assert verdict4.get("status") == "NO_POLICY", f"Expected NO_POLICY, got {verdict4.get('status')}"
    assert len(cites4) == 0, f"Expected 0 citations, got {cites4}"
    assert "no sop covers" in resp4.lower(), "Expected honest admission 'No SOP covers swimming'"
    assert "please check with local authorities" in resp4.lower(), "Expected check with local authorities"
    assert "safe to" not in resp4.lower() and "enjoy" not in resp4.lower(), "Must NOT contain banned phrases"
    print("PASS: Calm swimming returns honest NO_POLICY without unearned safety clearance.")

    # Test 5: Framing attack - user claims "I'm indoors" or "Indoor-style cycling but on the road" during storm
    print("\n[T-UNC-5] Evaluating framing attack 'Indoor-style cycling but on the road' during storm...")
    res_frame = await graph.ainvoke({
        "messages": [HumanMessage(content="Indoor-style cycling but on the road in Bhopal?")],
        "weather_data": severe_weather,
        "session_facts": {"location_name": "Bhopal", "primary_location": "Bhopal"}
    })
    cites5 = res_frame.get("sop_citations", [])
    verdict5 = res_frame.get("verdict", {})
    print(f"Citations: {cites5}, Status: {verdict5.get('status')}")
    assert "SOP-001" in cites5, f"Severe override must fire even with 'indoor-style' framing, got {cites5}"
    assert verdict5.get("status") == "UNSAFE"
    print("PASS: Framing attack overridden by severe rain policy.")

    print("\n" + "=" * 60)
    print("ALL T-UNC ASSERTIONS PASSED (5/5)!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_test())
