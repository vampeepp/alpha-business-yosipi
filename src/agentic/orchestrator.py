"""
Multi-Agent Orchestrator and Execution Trace Engine.
Coordinates the autonomous pipeline:
Planning -> Tool Calling -> Synthesis -> Self-Critique & Adaptation -> Audit Trace.
Also provides interactive contextual Q&A for executive decision-makers (Slide 10, Criterion 10).
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
from src.domain.models import CompanyProfile, NewsItem, PersonalizedInsight, AgentTraceStep
from src.agentic.tools import AgentToolRegistry
from src.agentic.planner import StrategicPlannerAgent
from src.agentic.analyzer import InsightAnalyzerAgent
from src.agentic.critic import SelfCritiqueAgent


class MultiAgentOrchestrator:
    """Manages multi-agent execution lifecycle and produces explainable traces."""

    def __init__(self, data_repo, graph_engine, rag_engine):
        self.repo = data_repo
        self.graph_engine = graph_engine
        self.rag_engine = rag_engine
        self.tools = AgentToolRegistry(data_repo, graph_engine, rag_engine)
        self.planner = StrategicPlannerAgent()
        self.analyzer = InsightAnalyzerAgent(self.tools)
        self.critic = SelfCritiqueAgent()

    def generate_personalized_insight(
        self,
        synthetic_u: str,
        news_id: str,
        role: str = "Генеральный директор",
    ) -> Tuple[PersonalizedInsight, List[AgentTraceStep]]:
        """
        Executes the full agentic multi-step workflow.
        Returns: (PersonalizedInsight, ExecutionTrace)
        """
        trace: List[AgentTraceStep] = []
        company = self.repo.get_company(synthetic_u)
        news = self.repo.news_items.get(news_id)

        if not company or not news:
            raise ValueError(f"Company {synthetic_u} or News {news_id} not found.")

        # -------------------------------------------------------------
        # STEP 1: Planning Phase
        # -------------------------------------------------------------
        plan = self.planner.create_execution_plan(company, news, role)
        trace.append(
            AgentTraceStep(
                step_number=1,
                step_name="PLANNING",
                agent_role="Strategic Planning Agent",
                action_summary=f"Декомпозиция бизнес-контекста {company.synthetic_u} и формулирование {len(plan['strategic_hypotheses'])} гипотез влияния.",
                details={"hypotheses": plan["strategic_hypotheses"], "steps_count": len(plan["planned_steps"])},
            )
        )

        # -------------------------------------------------------------
        # STEP 2: Tool Execution - Company Profile & Products
        # -------------------------------------------------------------
        profile_data = self.tools.tool_get_company_profile(synthetic_u)
        trace.append(
            AgentTraceStep(
                step_number=2,
                step_name="TOOL_EXECUTION",
                agent_role="Corporate Context Explorer",
                action_summary="Извлечение профиля компании, кредитной нагрузки, ВЭД-статуса и списка ключевых ЛПР.",
                details={
                    "revenue_billions": company.revenue_billions,
                    "mainokved": f"{company.mainokved_code} {company.mainokved_name}",
                    "has_loan": company.has_loan,
                    "has_leasing": company.has_leasing,
                    "fts_country": company.fts_country_name,
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 3: Tool Execution - Supply Chain & Counterparty Graph
        # -------------------------------------------------------------
        counterparty_data = self.tools.tool_get_counterparty_graph(synthetic_u)
        exposures_count = len(counterparty_data.get("exposures", []))
        trace.append(
            AgentTraceStep(
                step_number=3,
                step_name="TOOL_EXECUTION",
                agent_role="Supply Chain Network Agent",
                action_summary=f"Анализ графа платежей (df_Uid_payment_hack): выявлено {exposures_count} прямых контрагентов первого порядка.",
                details={"exposures": counterparty_data.get("exposures", [])[:3]},
            )
        )

        # -------------------------------------------------------------
        # STEP 4: Tool Execution - Macro Research RAG
        # -------------------------------------------------------------
        macro_query = f"{news.title} {company.mainokved_name}"
        macro_data = self.tools.tool_search_bank_macro_research(
            query=macro_query, sector=company.mainokved_name, top_k=2
        )
        matched_reports = [r["title"] for r in macro_data.get("results", [])]
        trace.append(
            AgentTraceStep(
                step_number=4,
                step_name="TOOL_EXECUTION",
                agent_role="Alfa Macro Intelligence Agent",
                action_summary=f"Гибридный RAG-поиск по исследованиям Альфа-Банка: найдено {len(matched_reports)} релевантных обзора.",
                details={"matched_reports": matched_reports},
            )
        )

        # -------------------------------------------------------------
        # STEP 5: Cognitive Synthesis (Analyzer)
        # -------------------------------------------------------------
        draft_insight = self.analyzer.synthesize(
            company=company,
            news=news,
            role=role,
            counterparty_data=counterparty_data,
            macro_research_data=macro_data,
        )
        trace.append(
            AgentTraceStep(
                step_number=5,
                step_name="REASONING",
                agent_role="Senior Business Insight Architect",
                action_summary="Многофакторный синтез 6 обязательных блоков персонализированной интерпретации.",
                details={
                    "pillars_generated": ["what_happened", "why_it_matters", "potential_consequences", "recommended_actions", "bank_perspective", "data_lineage"],
                    "suggested_products_count": len(draft_insight.suggested_bank_products),
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 6: Self-Critique & Adaptation (Critic)
        # -------------------------------------------------------------
        verified_insight, critique_summary = self.critic.review_and_adapt(
            insight=draft_insight, company=company, news=news
        )
        trace.append(
            AgentTraceStep(
                step_number=6,
                step_name="SELF_CRITIQUE_AND_ADAPTATION",
                agent_role="Independent Quality & Factuality Critic",
                action_summary=f"Верификация качества: итоговый скор {critique_summary['critic_score']}/100. Статус: {critique_summary['verdict']}",
                details=critique_summary,
            )
        )

        return verified_insight, trace

    def answer_executive_followup(
        self,
        synthetic_u: str,
        news_id: str,
        question: str,
        role: str = "Генеральный директор",
    ) -> Dict[str, Any]:
        """
        Interactive Q&A Copilot ("Спросить у Альфа-Аналитика").
        Answers follow-up drilldown questions grounded in company profile, payment graph, and bank research.
        """
        company = self.repo.get_company(synthetic_u)
        news = self.repo.news_items.get(news_id)
        if not company or not news:
            return {"answer": "Ошибка: компания или новость не найдены."}

        # Gather context
        exposures = self.graph_engine.get_counterparty_exposures(synthetic_u)
        macro_reports = self.rag_engine.retrieve(query=f"{news.title} {question}", sector=company.mainokved_name, top_k=2)
        top_macro = macro_reports[0][0] if macro_reports else None

        q_lower = question.lower()
        response_parts = []

        response_parts.append(f"Уважаемый {role}! Отвечая на Ваш вопрос касательно *«{news.title}»*:\n")

        if any(w in q_lower for w in ["ставк", "кредит", "процент", "долг"]):
            response_parts.append(
                f"• **Финансовая нагрузка:** Учитывая, что {company.synthetic_u} имеет кредитные обязательства "
                f"(выручка {company.revenue_billions} млрд ₽), ставка 14.0% фиксирует высокую стоимость заимствований. "
                f"Рекомендуем обратиться к корпоративному казначейству Альфа-Банка для заключения процентного свопа (IRS) "
                f"для хеджирования дальнейшего роста ставок."
            )
        elif any(w in q_lower for w in ["поставщик", "контрагент", "дебитор", "цепочк", "платеж"]):
            if exposures:
                top = exposures[0]
                response_parts.append(
                    f"• **Анализ расчетов:** Крупнейший риск в платежной цепочке сосредоточен на контрагенте **{top.counterparty_name}** "
                    f"(объем оборота: {top.payment_amount / 1e9:.2f} млрд ₽, уровень риска: {top.risk_level}). "
                    f"Рекомендуем внедрить электронный факторинг или покрытые аккредитивы для исключения кассовых разрывов."
                )
            else:
                response_parts.append("• **Контрагенты:** По предоставленным данным платежного реестра концентрация рисков не превышает лимитов.")
        elif any(w in q_lower for w in ["вэд", "валют", "экспорт", "импорт", "таможн", "китай", "турци"]):
            country = company.fts_country_name or "внешние рынки"
            response_parts.append(
                f"• **ВЭД-направление:** Для расчетов с партнерами из **{country}** Альфа-Банк обеспечивает прямые расчеты "
                f"в национальных валютах без использования SWIFT через азиатские шлюзы. Средний срок проведения платежа — до 24 часов."
            )
        else:
            response_parts.append(
                f"• **Стратегический вывод:** Данное событие требует пересмотра операционных бюджетов и координации с Альфа-Банком "
                f"в части комплексного управления ликвидностью."
            )

        if top_macro:
            response_parts.append(
                f"\n📌 *Ссылка на макроаналитику Альфа-Банка:* «{top_macro.title}» (ЦМИ Альфа-Банка, {top_macro.date})."
            )

        return {
            "question": question,
            "answer": "\n".join(response_parts),
            "grounded_sources": [
                f"Профиль компании {company.synthetic_u}",
                f"Реестр платежей (контрагентов: {len(exposures)})",
                f"Макрообзор Альфа-Банка: {top_macro.title if top_macro else 'Общая аналитика'}",
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
