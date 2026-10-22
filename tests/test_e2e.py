"""
End-to-end integration and verification test suite.
Simulates executive user scenarios, verifies all criteria from Hackathon Slides 9-10.
"""

import sys
import logging
from src.infrastructure.data_loader import DataRepository
from src.infrastructure.graph_engine import CounterpartyGraphEngine
from src.infrastructure.rag_engine import MacroResearchRAGEngine
from src.domain.scoring import PersonalizedScoringEngine
from src.agentic.orchestrator import MultiAgentOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AlfaNewsAnalytics.E2E")


def run_verification_suite() -> bool:
    """Executes full end-to-end scenario verification against all hackathon criteria."""
    logger.info("=== STARTING END-TO-END VERIFICATION SUITE ===")
    all_passed = True

    # 1. Data Ingestion & Indexing
    logger.info("Test 1: Verifying Data Repository loading...")
    repo = DataRepository()
    if len(repo.companies) == 0 or len(repo.news_items) == 0 or len(repo.macro_reports) == 0:
        logger.error("Data repository failed to load required records!")
        return False
    logger.info(f"✓ Loaded {len(repo.companies)} companies, {len(repo.macro_reports)} macro reports, {len(repo.news_items)} news items.")

    # 2. Graph Engine
    logger.info("Test 2: Verifying Counterparty Supply Chain Graph...")
    graph = CounterpartyGraphEngine(repo)
    exposures = graph.get_counterparty_exposures("U_AGRO_001")
    if len(exposures) == 0:
        logger.error("Failed to construct counterparty exposures for U_AGRO_001!")
        return False
    logger.info(f"✓ Found {len(exposures)} active counterparties for U_AGRO_001.")

    # 3. Hybrid RAG Engine
    logger.info("Test 3: Verifying Alfa Macro Research Hybrid RAG Engine...")
    rag = MacroResearchRAGEngine(repo)
    rag_results = rag.retrieve(query="Ключевая ставка Банка России", sector="Сельское хозяйство", top_k=2)
    if len(rag_results) == 0 or rag_results[0][1] <= 0:
        logger.error("RAG retrieval failed to find relevant macro reports!")
        return False
    logger.info(f"✓ RAG retrieved '{rag_results[0][0].title}' with score {rag_results[0][1]}.")

    # 4. Multi-Factor Personalized Scoring
    logger.info("Test 4: Verifying Multi-Factor Scoring Engine...")
    scorer = PersonalizedScoringEngine(graph)
    agro_comp = repo.get_company("U_AGRO_001")
    rate_news = repo.news_items.get("NEWS-2026-09-001")
    score = scorer.score(agro_comp, rate_news, role="Финансовый директор (CFO)")
    if score.total_score < 40:
        logger.error(f"Scoring engine produced unexpectedly low score: {score.total_score}")
        return False
    logger.info(f"✓ Personalized relevance score: {score.total_score}% (Priority: {score.priority_level}). Breakdown: {score.explanation}")

    # 5. Multi-Agent 6-Pillar Workflow & Traceability
    logger.info("Test 5: Verifying Multi-Agent Orchestrator, 6-Pillars, and Critic...")
    orchestrator = MultiAgentOrchestrator(repo, graph, rag)
    insight, trace = orchestrator.generate_personalized_insight(
        synthetic_u="U_AGRO_001", news_id="NEWS-2026-09-001", role="Генеральный директор"
    )

    # Check 6 pillars
    assert insight.what_happened, "Pillar 1 missing"
    assert insight.why_it_matters, "Pillar 2 missing"
    assert insight.potential_consequences, "Pillar 3 missing"
    assert insight.recommended_actions, "Pillar 4 missing"
    assert insight.bank_expert_perspective, "Pillar 5 missing"
    assert insight.data_lineage, "Pillar 6 missing"

    assert insight.impact_chain, "Impact chain missing"
    assert len(trace) == 8, f"Expected 8 steps, got {len(trace)}"

    logger.info(f"✓ 6-Pillar insight and Impact Chain generated successfully ({len(insight.impact_chain.steps)} causal steps).")
    logger.info(f"✓ Critic verification score: {insight.critic_review.get('critic_score')}/100. Verdict: {insight.critic_review.get('verdict')}")
    logger.info(f"✓ Agent execution trace recorded: {len(trace)} steps (Image 2 checklist verified).")

    # 6. Interactive Executive Q&A Copilot
    logger.info("Test 6: Verifying Interactive Executive Q&A Copilot...")
    copilot_ans = orchestrator.answer_executive_followup(
        synthetic_u="U_AGRO_001", news_id="NEWS-2026-09-001", question="Каковы риски дебиторской задолженности?", role="CFO"
    )
    if "answer" not in copilot_ans or len(copilot_ans["answer"]) < 30:
        logger.error("Executive Copilot failed to provide grounded answer!")
        return False
    logger.info(f"✓ Executive Copilot response generated with {len(copilot_ans['grounded_sources'])} grounded sources.")

    logger.info("=== ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY ===")
    return True


if __name__ == "__main__":
    success = run_verification_suite()
    sys.exit(0 if success else 1)
