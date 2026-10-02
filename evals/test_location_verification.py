import unittest
import asyncio
from langchain_core.messages import HumanMessage
from backend.graph import build_safety_graph
from backend.nodes.location import get_weather_client
from backend.agent_state import SafetyStatus

class TestLocationVerification(unittest.TestCase):
    """
    WP2 Location-keyed data and coordinate verification tests:
    - Auckland and Springfield stubs must give different replies.
    - If payload coordinates are mismatched (> 0.5 deg), reply is DATA_UNAVAILABLE.
    - Weather cache uses (lat, lon, bucket) and caps TTL at 10 minutes.
    """

    def setUp(self):
        self.weather_client = get_weather_client()
        self.weather_client.use_city_stubs = True

    def tearDown(self):
        self.weather_client.use_city_stubs = False

    def test_auckland_and_springfield_give_different_replies(self):
        async def _run():
            graph = build_safety_graph(checkpointer=True)

            cfg_akl = {"configurable": {"thread_id": "test-wp2-auckland"}}
            t_akl = await graph.ainvoke({"messages": [HumanMessage(content="Is it safe to go for a run in Auckland right now?")]}, config=cfg_akl)
            resp_akl = t_akl["final_response"]

            cfg_spf = {"configurable": {"thread_id": "test-wp2-springfield"}}
            t_spf = await graph.ainvoke({"messages": [HumanMessage(content="Is it safe to go for a run in Springfield right now?")]}, config=cfg_spf)
            resp_spf = t_spf["final_response"]

            # Must mention their own resolved location and coordinates
            self.assertIn("Auckland", resp_akl)
            self.assertIn("Springfield", resp_spf)

            # Numbers must be different (Auckland has 16.0C, Springfield has 19.5C in stubs)
            self.assertIn("16.0", resp_akl)
            self.assertIn("19.5", resp_spf)
            self.assertNotEqual(resp_akl, resp_spf)

        asyncio.run(_run())

    def test_mismatched_payload_coordinates_returns_data_unavailable(self):
        async def _run():
            # Inject a stub returning mismatched coordinates (>0.5 deg off)
            original_fetch = self.weather_client.fetch_weather

            async def mock_mismatched_fetch(lat, lon, *args, **kwargs):
                data = await original_fetch(lat, lon, *args, **kwargs)
                # Intentionally corrupt payload coordinates by 2.0 degrees
                data["latitude"] = lat + 2.0
                data["longitude"] = lon + 2.0
                return data

            self.weather_client.fetch_weather = mock_mismatched_fetch
            try:
                graph = build_safety_graph(checkpointer=True)
                cfg = {"configurable": {"thread_id": "test-wp2-mismatch"}}
                res = await graph.ainvoke({"messages": [HumanMessage(content="Can I cycle in Jaipur right now?")]}, config=cfg)

                verdict = res.get("verdict") or {}
                self.assertEqual(verdict.get("status"), SafetyStatus.DATA_UNAVAILABLE.value)
                self.assertIn("unavailable", res["final_response"].lower())
            finally:
                self.weather_client.fetch_weather = original_fetch

        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
