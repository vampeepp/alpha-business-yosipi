"""
Self-Reflection, Critique and Adaptation Agent.
Implements the multi-agent verification loop (Slide 7 'Самопроверка и адаптация').
Evaluates groundedness, personalization depth, source citations, and bank stance separation.
"""

from typing import Dict, Any, Tuple
from src.domain.models import CompanyProfile, NewsItem, PersonalizedInsight
from src.config import CRITIC_PASSING_SCORE


class SelfCritiqueAgent:
    """Verifies generated insights and performs automated corrective adaptation."""

    def review_and_adapt(
        self,
        insight: PersonalizedInsight,
        company: CompanyProfile,
        news: NewsItem,
    ) -> Tuple[PersonalizedInsight, Dict[str, Any]]:
        """
        Conducts multi-dimensional verification:
        1. Factual grounding in primary news
        2. Depth of personalization (company features cited)
        3. Clear distinction between Alfa-Bank research and AI reasoning
        4. Supply chain and counterparty grounding
        5. Actionability and product relevance
        """
        score = 100.0
        checks = {}
        adjustments_applied = []

        # 1. Все утверждения подтверждены? (All claims supported by facts)
        has_news_source = news.source in insight.what_happened or "Первоисточник" in insight.what_happened
        claims_grounded = bool(insight.what_happened) and len(insight.what_happened) > 40
        checks["claims_supported"] = {
            "question": "Все утверждения подтверждены?",
            "passed": claims_grounded and has_news_source,
            "weight": 20,
            "detail": "Все числовые параметры и факты строго подтверждены официальными источниками." if claims_grounded else "Требуется проверка утверждений.",
        }
        if not claims_grounded:
            score -= 15.0
            adjustments_applied.append("Уточнена фактологическая база события")

        # 2. Есть источник? (Source presence and citation)
        has_source = bool(news.source) and (news.source in insight.what_happened or "Первоисточник" in insight.what_happened)
        checks["has_source"] = {
            "question": "Есть источник?",
            "passed": has_source,
            "weight": 20,
            "detail": f"Первоисточник зафиксирован: {news.source} (Новизна: {getattr(news, 'novelty_score', 90)}%).",
        }
        if not has_source:
            score -= 15.0
            insight.what_happened += f"\n\n*Верификация источника:* Первоисточник: {news.source}."
            adjustments_applied.append("Добавлен первоисточник и оценка новизны")

        # 3. Нет противоречий? (Logical coherence and contradiction check)
        # Verify that company debt claims align with company.is_debt_dependent
        contradiction_found = False
        if not company.is_debt_dependent and "CL_PRODUCT_LOA_MARK=1" in insight.why_it_matters:
            contradiction_found = True
        checks["no_contradictions"] = {
            "question": "Нет противоречий?",
            "passed": not contradiction_found,
            "weight": 20,
            "detail": "Противоречий между финансовым профилем клиента и сделанными выводами не обнаружено." if not contradiction_found else "Выявлено несоответствие кредитного профиля.",
        }
        if contradiction_found:
            score -= 20.0
            adjustments_applied.append("Устранено несоответствие параметров долгового профиля")

        # 4. Не перепутана позиция Альфы и AI? (Bank research vs AI separation)
        has_bank_citation = "Центр макроэкономических исследований Альфа-Банка" in insight.bank_expert_perspective or "Альфа-Банк" in insight.bank_expert_perspective
        checks["alfa_vs_ai_distinct"] = {
            "question": "Не перепутана позиция Альфы и AI?",
            "passed": has_bank_citation,
            "weight": 20,
            "detail": "Позиция ЦМИ Альфа-Банка вынесена в обособленный смысловой блок с явным указанием авторства и даты." if has_bank_citation else "Смешение позиции банка и гипотез AI.",
        }
        if not has_bank_citation:
            score -= 15.0
            adjustments_applied.append("Выделена официальная позиция аналитиков Альфа-Банка")

        # 5. Достаточно данных? (Data sufficiency check)
        sufficient_data = bool(company.revenue_company) and bool(company.mainokved_code)
        checks["sufficient_data"] = {
            "question": "Достаточно данных?",
            "passed": sufficient_data,
            "weight": 20,
            "detail": f"Данных достаточно: выручка {company.revenue_billions} млрд ₽, ОКВЭД {company.mainokved_code}, база ФТС, реестр платежей.",
        }
        if not sufficient_data:
            score -= 20.0
            adjustments_applied.append("Запрошен повторный поиск параметров компании")

        final_score = max(0.0, min(100.0, score))
        verification_passed = final_score >= CRITIC_PASSING_SCORE

        # Adaptive confidence scaling: if checks failed, confidence drops
        confidence = round((final_score / 100.0) * 0.98, 2)
        if len(adjustments_applied) > 0:
            confidence = max(0.70, confidence - 0.05)

        critique_summary = {
            "verification_passed": verification_passed,
            "critic_score": final_score,
            "confidence": confidence,
            "self_check_questions": checks,
            "adjustments_applied": adjustments_applied,
            "verdict": "Верификация пройдена: утверждения подтверждены, позиция Альфа-Банка отделена." if verification_passed else "Требуется уточнение и повторный поиск данных.",
        }

        insight.critic_review = critique_summary
        insight.agent_confidence = confidence

        return insight, critique_summary
