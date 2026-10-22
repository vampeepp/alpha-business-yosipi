"""
Strategic Planning Agent.
Analyzes the corporate context and news event to construct a dynamic,
multi-step execution plan tailored to the enterprise decision-maker (Slide 7).
"""

from typing import Dict, Any, List
from src.domain.models import CompanyProfile, NewsItem


class StrategicPlannerAgent:
    """Formulates dynamic intelligence retrieval and analysis plans."""

    def create_execution_plan(self, company: CompanyProfile, news: NewsItem, role: str) -> Dict[str, Any]:
        """
        Builds a structured plan:
        1. Contextual hypothesis formulation
        2. Required data retrieval steps
        3. Financial exposure focus areas
        4. Validation & reflection criteria
        """
        hypotheses = []

        # Formulate core hypotheses based on company characteristics
        if company.is_debt_dependent and any(kw in news.title.lower() for kw in ["ставк", "цб", "кредит", "инфляц"]):
            hypotheses.append("Высокая чувствительность финансовых расходов (Interest Expense) к уровню ключевой ставки ЦБ.")

        if company.has_foreign_trade and (company.fts_country_name or "вэд" in news.tags or "экспорт" in news.tags):
            hypotheses.append(f"Риск сжатия экспортно-импортной маржи и задержки платежей в направлении {company.fts_country_name or 'ВЭД'}.")

        if company.mainokved_code in ["01.11", "20.15", "24.10", "47.11"]:
            hypotheses.append(f"Прямое отраслевое воздействие на цепочку создания стоимости в сегменте '{company.mainokved_name}'.")

        if not hypotheses:
            hypotheses.append("Косвенное макроэкономическое влияние на операционные издержки и потребительский спрос.")

        steps = [
            {
                "step_id": 1,
                "tool": "get_company_profile",
                "purpose": f"Извлечь детальный профиль {company.synthetic_u}, параметры кредитного портфеля и ВЭД.",
                "args": {"synthetic_u": company.synthetic_u},
            },
            {
                "step_id": 2,
                "tool": "get_counterparty_graph",
                "purpose": "Определить ключевых поставщиков и покупателей для оценки риска передачи шока по цепочке поставок.",
                "args": {"synthetic_u": company.synthetic_u},
            },
            {
                "step_id": 3,
                "tool": "search_bank_macro_research",
                "purpose": "Найти профильные исследования Центра макроэкономических исследований Альфа-Банка для официальной позиции банка.",
                "args": {"query": f"{news.title} {company.mainokved_name}", "sector": company.mainokved_name},
            },
            {
                "step_id": 4,
                "tool": "synthesize_6_pillar_insight",
                "purpose": "Сформировать глубокую персонализированную интерпретацию по 6 обязательным блокам с разделением позиции банка и выводов AI.",
                "args": {"role": role},
            },
            {
                "step_id": 5,
                "tool": "self_critique_and_verify",
                "purpose": "Провести самопроверку на фактологическую точность, отсутствие галлюцинаций и качество продуктовых предложений.",
                "args": {},
            },
        ]

        return {
            "client_id": company.synthetic_u,
            "news_id": news.news_id,
            "target_persona": role,
            "strategic_hypotheses": hypotheses,
            "planned_steps": steps,
        }
