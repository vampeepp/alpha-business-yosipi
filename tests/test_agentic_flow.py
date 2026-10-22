"""
Unit tests for the Multi-Agent System (Planner, Tools, Analyzer, Critic, Orchestrator).
"""

import unittest
from src.infrastructure.data_loader import DataRepository
from src.infrastructure.graph_engine import CounterpartyGraphEngine
from src.infrastructure.rag_engine import MacroResearchRAGEngine
from src.agentic.orchestrator import MultiAgentOrchestrator


class TestAgenticFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo = DataRepository()
        cls.graph = CounterpartyGraphEngine(cls.repo)
        cls.rag = MacroResearchRAGEngine(cls.repo)
        cls.orchestrator = MultiAgentOrchestrator(cls.repo, cls.graph, cls.rag)

    def test_full_agentic_execution_and_trace(self):
        """Verifies multi-step agent flow generates 6 pillars and observable trace."""
        synthetic_u = "U_AGRO_001"
        news_id = "NEWS-2026-09-001"  # Key Rate news

        insight, trace = self.orchestrator.generate_personalized_insight(
            synthetic_u=synthetic_u, news_id=news_id, role="Финансовый директор (CFO)"
        )

        # 1. Verify 6 pillars exist and are non-empty
        self.assertTrue(len(insight.what_happened) > 50)
        self.assertTrue(len(insight.why_it_matters) > 50)
        self.assertTrue(len(insight.potential_consequences) > 50)
        self.assertTrue(len(insight.recommended_actions) > 50)
        self.assertTrue(len(insight.bank_expert_perspective) > 50)
        self.assertIn("client_features_utilized", insight.data_lineage)

        # 2. Verify distinction of Alfa-Bank research
        self.assertIn("Альфа-Банк", insight.bank_expert_perspective)

        # 3. Verify Critic review
        self.assertGreaterEqual(insight.critic_review.get("critic_score", 0), 85.0)
        self.assertTrue(insight.critic_review.get("verification_passed", False))

        # 4. Verify Trace has all 6 steps
        self.assertEqual(len(trace), 6)
        step_names = [t.step_name for t in trace]
        self.assertEqual(
            step_names,
            ["PLANNING", "TOOL_EXECUTION", "TOOL_EXECUTION", "TOOL_EXECUTION", "REASONING", "SELF_CRITIQUE_AND_ADAPTATION"]
        )

    def test_interactive_executive_copilot(self):
        """Verifies interactive Q&A assistant answers follow-up drilldowns."""
        ans = self.orchestrator.answer_executive_followup(
            synthetic_u="U_AGRO_001",
            news_id="NEWS-2026-09-001",
            question="Как нам захеджировать процентные расходы по кредиту?",
            role="Руководитель казначейства"
        )
        self.assertIn("answer", ans)
        self.assertIn("хеджирован", ans["answer"].lower())
        self.assertTrue(len(ans["grounded_sources"]) > 0)


if __name__ == "__main__":
    unittest.main()
