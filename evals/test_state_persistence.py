import unittest
import asyncio
from langchain_core.messages import HumanMessage
from backend.graph import build_safety_graph
from backend.nodes.location import get_weather_client

class TestStatePersistence(unittest.TestCase):
    """
    WP1 State Hygiene Tests:
    - After 'Xqzvbnmtrw cycling,' 'cycling?' still uses Bhopal.
    - After the IMD question, a walk question has no IMD banner.
    - Failed geocode must NEVER write to SessionState.
    """

    def setUp(self):
        self.weather_client = get_weather_client()
        self.weather_client.use_city_stubs = True

    def tearDown(self):
        self.weather_client.use_city_stubs = False

    def test_failed_geocode_never_overwrites_session_state(self):
        async def _run():
            graph = build_safety_graph(checkpointer=True)
            config = {"configurable": {"thread_id": "test-wp1-geocode"}}

            # Turn 1: Valid city Bhopal
            t1 = await graph.ainvoke({"messages": [HumanMessage(content="Is it safe to cycle in Bhopal today?")]}, config=config)
            self.assertIn("Bhopal", t1["final_response"])
            sess = t1.get("session_state") or {}
            self.assertEqual(sess.get("last_good_location", {}).get("name"), "Bhopal")

            # Turn 2: Invalid gibberish city Xqzvbnmtrw
            t2 = await graph.ainvoke({"messages": [HumanMessage(content="Xqzvbnmtrw cycling")]}, config=config)
            self.assertIn("Could not resolve location", t2["final_response"])
            # Ensure session_state still holds Bhopal, NOT Xqzvbnmtrw!
            sess2 = t2.get("session_state") or {}
            self.assertEqual(sess2.get("last_good_location", {}).get("name"), "Bhopal")

            # Turn 3: "cycling?" follow-up should still use Bhopal
            t3 = await graph.ainvoke({"messages": [HumanMessage(content="cycling?")]}, config=config)
            self.assertIn("Bhopal", t3["final_response"])

        asyncio.run(_run())

    def test_no_stale_imd_banner_on_subsequent_turn(self):
        async def _run():
            graph = build_safety_graph(checkpointer=True)
            config = {"configurable": {"thread_id": "test-wp1-imd"}}

            # Turn 1: Setup Bhopal location
            await graph.ainvoke({"messages": [HumanMessage(content="Is it safe to cycle in Bhopal today?")]}, config=config)

            # Turn 2: IMD question
            t2 = await graph.ainvoke({"messages": [HumanMessage(content="Has the IMD issued a warning for my area in Bhopal?")]}, config=config)
            self.assertIn("Data Source Notice", t2["final_response"])

            # Turn 3: Walk question in Bhopal
            t3 = await graph.ainvoke({"messages": [HumanMessage(content="Can I go for a walk in Bhopal right now?")]}, config=config)
            # Must NOT contain IMD banner or notice
            self.assertNotIn("Data Source Notice", t3["final_response"])
            self.assertNotIn("IMD", t3["final_response"])
            self.assertIn("Bhopal", t3["final_response"])

        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
