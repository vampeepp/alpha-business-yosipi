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

        # Check 1: Factual grounding in primary news
        has_news_source = news.source in insight.what_happened or "Первоисточник" in insight.what_happened
        checks["news_groundedness"] = {
            "passed": has_news_source,
            "weight": 20,
            "detail": "Первоисточник новости корректно зафиксирован." if has_news_source else "Отсутствует явная ссылка на первоисточник новости.",
        }
        if not has_news_source:
            score -= 15.0
            insight.what_happened += f"\n\n*Верификация критика:* Добавлена обязательная ссылка на источник {news.source}."
            adjustments_applied.append("Добавлена валидация первоисточника новости")

        # Check 2: Depth of client personalization
        has_revenue = str(company.revenue_billions) in insight.why_it_matters or "выручк" in insight.why_it_matters.lower()
        has_okved = company.mainokved_code in insight.why_it_matters or company.mainokved_name.lower() in insight.why_it_matters.lower()
        personalization_passed = has_revenue and has_okved
        checks["personalization_depth"] = {
            "passed": personalization_passed,
            "weight": 30,
            "detail": "Анализ строго привязан к выручке и отраслевому коду компании." if personalization_passed else "Недостаточная глубина привязки к параметрам компании.",
        }
        if not personalization_passed:
            score -= 20.0
            insight.why_it_matters = (
                f"**Параметры компании {company.synthetic_u}:** Выручка {company.revenue_billions} млрд ₽, "
                f"ОКВЭД {company.mainokved_code} ({company.mainokved_name}).\n" + insight.why_it_matters
            )
            adjustments_applied.append("Усилена персонализация по ОКВЭД и масштабу выручки")

        # Check 3: Clear separation of Bank research vs AI deduction (Criterion 3)
        has_bank_citation = "Центр макроэкономических исследований Альфа-Банка" in insight.bank_expert_perspective or "Альфа-Банк" in insight.bank_expert_perspective
        checks["bank_research_distinction"] = {
            "passed": has_bank_citation,
            "weight": 25,
            "detail": "Позиция экспертов ЦМИ Альфа-Банка четко отделена от выводов нейросетевого ассистента." if has_bank_citation else "Смешение позиции банка и гипотез AI.",
        }
        if not has_bank_citation:
            score -= 15.0

        # Check 4: Data Lineage completeness
        lineage = insight.data_lineage
        has_lineage = bool(lineage.get("client_features_utilized")) and bool(lineage.get("primary_news_source"))
        checks["data_lineage"] = {
            "passed": has_lineage,
            "weight": 15,
            "detail": "Полный аудит источников и клиентских признаков сформирован." if has_lineage else "Неполный граф происхождения данных.",
        }
        if not has_lineage:
            score -= 10.0

        # Check 5: Banking product relevance
        has_products = len(insight.suggested_bank_products) > 0
        checks["banking_product_fit"] = {
            "passed": has_products,
            "weight": 10,
            "detail": f"Подобрано {len(insight.suggested_bank_products)} нативных корпоративных продуктов Альфа-Банка." if has_products else "Банковские решения не предложены.",
        }

        final_score = max(0.0, min(100.0, score))
        verification_passed = final_score >= CRITIC_PASSING_SCORE

        critique_summary = {
            "verification_passed": verification_passed,
            "critic_score": final_score,
            "checks": checks,
            "adjustments_applied": adjustments_applied,
            "verdict": "Одобрено для публикации в интернет-банке Альфа-Бизнес." if verification_passed else "Требуется доработка параметров.",
        }

        insight.critic_review = critique_summary
        insight.agent_confidence = round(final_score / 100.0, 2)

        return insight, critique_summary
