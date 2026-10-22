"""
Tool definitions and execution registry for the Multi-Agent System.
Implements data access and financial analysis tools used by the Planner and Analyzer.
"""

from typing import Dict, Any, List, Optional
from src.domain.models import CompanyProfile, NewsItem, AlfaMacroReport


class AgentToolRegistry:
    """Registry providing standard tools for agents to query corporate data and research."""

    def __init__(self, data_repo, graph_engine, rag_engine):
        self.repo = data_repo
        self.graph_engine = graph_engine
        self.rag_engine = rag_engine

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Dispatches tool execution dynamically with error boundaries."""
        method = getattr(self, f"tool_{tool_name}", None)
        if not method:
            return {"error": f"Tool '{tool_name}' not found in registry."}
        try:
            return method(**kwargs)
        except Exception as e:
            return {"error": f"Tool execution failed for '{tool_name}': {str(e)}"}

    def tool_get_company_profile(self, synthetic_u: str) -> Dict[str, Any]:
        """Fetches full enterprise corporate profile and product holdings."""
        company = self.repo.get_company(synthetic_u)
        if not company:
            return {"error": f"Company {synthetic_u} not found"}
        persons = self.repo.get_persons_for_company(synthetic_u)
        return {
            "profile": company.to_dict(),
            "linked_persons": [p.to_dict() for p in persons],
        }

    def tool_get_counterparty_graph(self, synthetic_u: str) -> Dict[str, Any]:
        """Fetches first-degree suppliers, buyers, transaction volumes and exposure levels."""
        exposures = self.graph_engine.get_counterparty_exposures(synthetic_u)
        return {
            "synthetic_u": synthetic_u,
            "total_counterparties": len(exposures),
            "exposures": [exp.to_dict() for exp in exposures],
        }

    def tool_search_bank_macro_research(self, query: str, sector: str = "", top_k: int = 2) -> Dict[str, Any]:
        """Queries Alfa-Bank Macro Research repository via hybrid RAG."""
        results = self.rag_engine.retrieve(query=query, sector=sector, top_k=top_k)
        items = []
        for report, score, passage in results:
            items.append({
                "id": report.id,
                "title": report.title,
                "date": report.date,
                "author": report.author,
                "relevance_score": score,
                "summary": report.summary,
                "full_text": report.full_text,
                "key_indicators": report.key_indicators,
                "bank_recommendations": report.bank_recommendations,
                "matched_passage": passage,
            })
        return {"query": query, "sector": sector, "matches_count": len(items), "results": items}

    def tool_get_news_details(self, news_id: str) -> Dict[str, Any]:
        """Fetches full news content, entities, category and metadata."""
        news = self.repo.news_items.get(news_id)
        if not news:
            return {"error": f"News item {news_id} not found"}
        return {"news": news.to_dict()}

    def tool_match_banking_solutions(self, company_u: str, risk_domains: List[str]) -> List[Dict[str, str]]:
        """
        Determines targeted Alfa-Bank corporate banking products (Slide 13, Native Advertising)
        based on company profile and identified risk factors.
        """
        company = self.repo.get_company(company_u)
        products = []
        if not company:
            return products

        # If interest rate risk or debt is high
        if any(d in ["ДКП", "Ставка", "Кредиты", "Оборотный капитал"] for d in risk_domains):
            if company.has_loan:
                products.append({
                    "product_name": "Хеджирование процентных рисков (IRS)",
                    "category": "Казначейские операции",
                    "benefit": "Фиксация процентной ставки по кредитному портфелю без переплаты при росте КС ЦБ РФ.",
                    "action_text": "Запросить расчет структуры процентного свопа",
                })
            products.append({
                "product_name": "Электронный факторинг Альфа-Банка",
                "category": "Финансирование цепочек поставок",
                "benefit": "Моментальное получение до 100% выручки по контрактам с отсрочкой платежа без залогов и кредитной нагрузки.",
                "action_text": "Подключить онлайн-факторинг",
            })

        # If foreign trade or customs risk
        if company.has_foreign_trade or any("ВЭД" in d or "Экспорт" in d or "Таможня" in d for d in risk_domains):
            country = company.fts_country_name or "АТР"
            products.append({
                "product_name": f"ВЭД-сопровождение и прямые расчеты в национальных валютах ({country})",
                "category": "Международный бизнес",
                "benefit": f"Прямые корреспондентские счета, ускоренный валютный контроль и форвардные контракты на поставку валюты.",
                "action_text": "Открыть мультивалютный счет ВЭД",
            })

        # If equipment or machinery Capex is needed
        if company.has_leasing or any("Логистика" in d or "Оборудование" in d or "Машиностроение" in d for d in risk_domains):
            products.append({
                "product_name": "Субсидированный лизинг Альфа-Лизинг",
                "category": "Лизинг",
                "benefit": "Приобретение грузового транспорта, спецтехники и оборудования с господдержкой до 15% скидки на аванс.",
                "action_text": "Оставить заявку на экспресс-лизинг",
            })

        # If deposit / excess liquidity
        if company.has_deposit or any("Ликвидность" in d for d in risk_domains):
            products.append({
                "product_name": "Автоматический овернайт-депозит 'Умный остаток'",
                "category": "Управление ликвидностью",
                "benefit": "Доходность до КС ЦБ РФ минус 0.5% на неснижаемые остатки расчетного счета без блокировки средств.",
                "action_text": "Настроить авто-размещение остатков",
            })

        return products
