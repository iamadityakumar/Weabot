import unittest
from backend.nodes.guards_node import guards_node, BANNED_PHRASES
from backend.agent_state import AgentState

class TestGuards(unittest.TestCase):
    """
    WP6 Guards Node Tests:
    - Banned phrases rejection: 'safe to', 'enjoy', 'proceed with caution', 'you will not', 'recommended'.
    - Untraced number detection (prevents hallucinated advice or numbers).
    - Unapproved SOP citations rejection.
    - Verified clean text passes unmutated.
    """

    def setUp(self):
        self.mock_evaluated_sops = [
            {"id": "SOP-001", "title": "Severe Rain", "advice": "Seek immediate shelter.", "conditions": ["precipitation >= 5.0"]},
            {"id": "SOP-003", "title": "Heat Stress", "advice": "Take breaks every 15 minutes.", "conditions": ["apparent_temperature >= 32.0"]}
        ]
        self.mock_fired_sops = [self.mock_evaluated_sops[1]]
        self.mock_weather = {
            "current": {
                "temperature_2m": 33.5,
                "apparent_temperature": 35.0,
                "precipitation": 0.0,
                "wind_speed_10m": 12.0,
                "wind_gusts_10m": 18.0,
                "uv_index": 4.5
            }
        }
        self.mock_turn_state = {
            "raw_query": "Is it fine to jog in Bhopal today?",
            "activity_label": "jogging",
            "resolved_location": {
                "name": "Bhopal",
                "latitude": 23.25,
                "longitude": 77.40
            }
        }

    def test_banned_phrases_trigger_fallback(self):
        for phrase in BANNED_PHRASES:
            tainted_text = f"**Bhopal (23.25°N, 77.40°E)**\n\nIt is {phrase} right now.\n\n• SOPs Evaluated: [SOP-001, SOP-003]\n• SOPs Fired: [SOP-003]"
            state: AgentState = {
                "final_response": tainted_text,
                "effective_weather": self.mock_weather,
                "evaluated_sops": self.mock_evaluated_sops,
                "fired_sops": self.mock_fired_sops,
                "turn_state": self.mock_turn_state
            }
            res = guards_node(state)
            clean_resp = res["final_response"]
            self.assertNotIn(phrase, clean_resp.lower(), f"Banned phrase '{phrase}' was not sanitized!")

    def test_untraced_hallucinated_numbers_trigger_fallback(self):
        # 999.88 is not in payload, coords, SOPs, or user query
        hallucinated_text = "**Bhopal (23.25°N, 77.40°E)**\n\nAir quality is 999.88.\n\n• SOPs Evaluated: [SOP-001, SOP-003]\n• SOPs Fired: [None]"
        state: AgentState = {
            "final_response": hallucinated_text,
            "effective_weather": self.mock_weather,
            "evaluated_sops": self.mock_evaluated_sops,
            "fired_sops": [],
            "turn_state": self.mock_turn_state
        }
        res = guards_node(state)
        self.assertNotIn("999.88", res["final_response"])
        self.assertIn("Evaluated Standard Operating Procedures", res["final_response"])

    def test_uncited_sop_id_triggers_fallback(self):
        # SOP-099 was not in evaluated_sops
        illegal_citation_text = "**Bhopal (23.25°N, 77.40°E)**\n\nTriggered [SOP-099].\n\n• SOPs Evaluated: [SOP-001, SOP-003]"
        state: AgentState = {
            "final_response": illegal_citation_text,
            "effective_weather": self.mock_weather,
            "evaluated_sops": self.mock_evaluated_sops,
            "fired_sops": [],
            "turn_state": self.mock_turn_state
        }
        res = guards_node(state)
        self.assertNotIn("SOP-099", res["final_response"])
        self.assertIn("Evaluated Standard Operating Procedures", res["final_response"])

    def test_valid_text_passes_unchanged(self):
        valid_text = (
            "**Bhopal (23.25°N, 77.40°E)**\n\n"
            "• **Target Time**: Current model conditions\n\n"
            "• **Current model conditions**: Temperature 33.5°C, Apparent temperature 35.0°C, "
            "Wind 12.0 km/h (3.33 m/s, 7.46 mph), Gusts up to 18.0 km/h (5.0 m/s, 11.18 mph), "
            "Precipitation 0.0 mm, UV Index 4.5.\n\n"
            "Take breaks every 15 minutes.\n\n"
            "• **SOPs Evaluated**: [SOP-001, SOP-003]\n"
            "• **SOPs Fired**: [SOP-003]"
        )
        state: AgentState = {
            "final_response": valid_text,
            "effective_weather": self.mock_weather,
            "evaluated_sops": self.mock_evaluated_sops,
            "fired_sops": self.mock_fired_sops,
            "turn_state": self.mock_turn_state
        }
        res = guards_node(state)
        self.assertEqual(res["final_response"], valid_text)

if __name__ == "__main__":
    unittest.main()
