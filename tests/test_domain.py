"""
Unit tests for Domain Models and Personalized Scoring.
"""

import unittest
from src.infrastructure.data_loader import DataRepository
from src.infrastructure.graph_engine import CounterpartyGraphEngine
from src.domain.scoring import PersonalizedScoringEngine


class TestDomainAndScoring(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo = DataRepository()
        cls.graph = CounterpartyGraphEngine(cls.repo)
        cls.scorer = PersonalizedScoringEngine(cls.graph)

    def test_large_enterprise_threshold(self):
        """Verifies that companies are classified as large enterprises (>15B RUB)."""
        agro = self.repo.get_company("U_AGRO_001")
        self.assertIsNotNone(agro)
        self.assertTrue(agro.is_large_enterprise)
        self.assertGreaterEqual(agro.revenue_company, 15_000_000_000.0)

    def test_debt_sensitivity_scoring(self):
        """Verifies that an indebted company receives higher score for Key Rate news."""
        rate_news = self.repo.news_items.get("NEWS-2026-09-001")
        self.assertIsNotNone(rate_news)

        indebted_comp = self.repo.get_company("U_AGRO_001")  # has_loan=1, has_leasing=1
        tech_comp = self.repo.get_company("U_TECH_005")      # has_loan=0, has_leasing=0

        score_indebted = self.scorer.score(indebted_comp, rate_news)
        score_tech = self.scorer.score(tech_comp, rate_news)

        self.assertGreater(score_indebted.debt_exposure_score, score_tech.debt_exposure_score)
        self.assertGreater(score_indebted.total_score, score_tech.total_score)

    def test_sector_okved_scoring(self):
        """Verifies that agricultural news scores highest for agricultural company."""
        grain_news = self.repo.news_items.get("NEWS-2026-09-002")
        agro_comp = self.repo.get_company("U_AGRO_001")
        metall_comp = self.repo.get_company("U_METALL_002")

        score_agro = self.scorer.score(agro_comp, grain_news)
        score_metall = self.scorer.score(metall_comp, grain_news)

        self.assertGreater(score_agro.direct_sector_score, score_metall.direct_sector_score)
        self.assertEqual(score_agro.priority_level, "CRITICAL")


if __name__ == "__main__":
    unittest.main()
