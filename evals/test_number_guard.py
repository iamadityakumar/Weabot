import asyncio
import sys
from pathlib import Path
from langchain_core.messages import HumanMessage

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.nodes.number_guard import validate_and_guard_numbers

def run_number_guard_tests():
    print("=" * 60)
    print("RUNNING RUNTIME NUMBER GUARD VERIFICATION SUITE")
    print("=" * 60)

    # State with known weather metrics
    state = {
        "final_response": "Observed wind speed is 15.0 km/h (4.2 m/s, 9.3 mph) with temperature 28°C.",
        "effective_weather": {
            "current": {
                "temperature_2m": 28.0,
                "wind_speed_10m": 15.0,
                "wind_gusts_10m": 20.0,
                "precipitation": 0.0,
                "precipitation_probability": 0
            }
        },
        "matched_sops": [
            {
                "id": "SOP-004",
                "title": "Wind Safety",
                "severity": "moderate",
                "advice": "Elevated wind speeds exceeding 25 km/h require reduced speed.",
                "conditions": [{"field": "wind_speed_10m", "op": ">=", "value": 15.0}]
            }
        ],
        "messages": [HumanMessage(content="Is it windy in Bhopal today?")],
        "extracted_intent": {"activity": "cycling"},
        "session_facts": {"location_name": "Bhopal"}
    }

    # Test 1: Verified valid response passes through
    res1 = validate_and_guard_numbers(state)
    assert not res1["number_guard_triggered"], f"Expected pass, but guard triggered on: {res1.get('unauthorized_numbers')}"
    print("[PASS] Test 1: Verified telemetry numbers and derived conversions pass cleanly.")

    # Test 2: Injected hallucinated metric triggers number guard fallback
    state_hallucinated = dict(state)
    state_hallucinated["final_response"] = "The wind speed is 15.0 km/h and solar radiation is 888.5 watts/m2."
    res2 = validate_and_guard_numbers(state_hallucinated)
    assert res2["number_guard_triggered"], "Expected number guard to trigger on unauthorized 888.5"
    assert "888.5" in res2["unauthorized_numbers"]
    assert "runtime number guard" in res2["final_response"].lower()
    print("[PASS] Test 2: Injected untraced number (888.5) intercepted and safely replaced with fallback.")

    print("\n" + "=" * 60)
    print("ALL RUNTIME NUMBER GUARD ASSERTIONS PASSED (2/2)!")
    print("=" * 60)

if __name__ == "__main__":
    run_number_guard_tests()
