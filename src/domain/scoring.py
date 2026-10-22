import re
from typing import Dict, Any, List, Tuple
from src.domain.models import CompanyProfile, NewsItem, RelevanceScore


class PersonalizedScoringEngine:
    """Calculates enterprise-grade relevance score for a company-news pair."""

    SECTOR_KEYWORDS = {
        "01.11": ["зерно", "зерновых", "пшеница", "пшеницы", "кукуруза", "апк", "сельхоз", "урожай", "пошлины", "минсельхоз", "посевная", "элеватор"],
        "24.10": ["металл", "металлопрокат", "сталь", "чугун", "прокат", "ферросплавы", "ржд", "бам", "транссиб", "китай", "руда"],
        "47.11": ["ритейл", "розничная торговля", "потребительский", "акорт", "полка", "стм", "дискаунтер", "чек", "продукты питания"],
        "20.15": ["удобрения", "удобрений", "карбамид", "селитра", "газ", "химия", "индия", "азот", "сырье"],
        "62.01": ["it-сектор", "софт", "программное обеспечение", "цифровизация", "облачные сервисы", "кибербезопасность", "дата-центр"],
        "52.29": ["логистика", "логистических", "транспорт", "контейнеры", "порт", "владивосток", "фрахт", "перевозки", "таможня", "зеленый коридор"],
        "28.30": ["машиностроение", "тракторы", "комбайны", "сельхозтехника", "программа 1432", "минпромторг", "субсидии", "лизинг"],
    }

    DEBT_KEYWORDS = ["ставка", "ставки", "ставку", "цб", "банк россии", "кредит", "кредитов", "инфляция", "дкп", "облигации", "бонды", "флоатер", "ликвидность"]
    FX_TRADE_KEYWORDS = ["экспорт", "экспортная", "импорт", "пошлина", "пошлины", "вэд", "таможня", "фтс", "китай", "турция", "индия", "валюта", "рубль"]
    WORKING_CAPITAL_KEYWORDS = ["факторинг", "дебиторка", "отсрочка", "отсрочки", "кассовый разрыв", "платежи", "поставщики", "оборотный капитал"]

    def __init__(self, graph_engine):
        self.graph_engine = graph_engine

    @staticmethod
    def _matches_keyword(kw: str, text: str) -> bool:
        """Robust whole-word or token prefix match avoiding false substrings."""
        pattern = r"(?<![a-zа-яё0-9])" + re.escape(kw)
        return bool(re.search(pattern, text, re.IGNORECASE))

    def score(self, company: CompanyProfile, news: NewsItem, role: str = "Генеральный директор") -> RelevanceScore:
        """
        Computes composite relevance score (0 - 100) taking into account:
        1. Direct sector/OKVED match
        2. Debt & Monetary policy sensitivity
        3. Foreign trade & customs sensitivity
        4. Supply chain ripple effect (counterparty exposure)
        5. Working capital & factoring sensitivity
        6. Persona / Role weighting (CEO, CFO, Head of Treasury, Chief Accountant)
        """
        news_text = f"{news.title} {news.summary} {news.full_content} {' '.join(news.tags)} {' '.join(news.entities)}".lower()

        # 1. Direct Sector Score (0 - 35 pts)
        direct_sector_score = 0.0
        relevant_keywords = self.SECTOR_KEYWORDS.get(company.mainokved_code, [])
        matches = [kw for kw in relevant_keywords if self._matches_keyword(kw, news_text)]
        if matches:
            direct_sector_score = min(35.0, 18.0 + len(matches) * 5.0)

        # 2. Macro & Debt Exposure Score (0 - 45 pts)
        debt_score = 0.0
        debt_matches = [kw for kw in self.DEBT_KEYWORDS if self._matches_keyword(kw, news_text)]
        if debt_matches:
            if company.is_debt_dependent:
                debt_score = min(45.0, 24.0 + len(debt_matches) * 4.0)
            else:
                debt_score = 6.0

            if company.has_deposit:
                debt_score += 4.0

        # 3. Foreign Trade Score (0 - 25 pts)
        trade_score = 0.0
        trade_matches = [kw for kw in self.FX_TRADE_KEYWORDS if self._matches_keyword(kw, news_text)]
        if trade_matches:
            if company.has_foreign_trade:
                base_trade = 12.0
                if company.fts_country_name and self._matches_keyword(company.fts_country_name, news_text):
                    base_trade += 10.0
                trade_score = min(25.0, base_trade + len(trade_matches) * 2.5)

        # 4. Counterparty & Supply Chain Spillover Score (0 - 25 pts)
        supply_chain_score = 0.0
        exposures = self.graph_engine.get_counterparty_exposures(company.synthetic_u)
        affected_counterparties = []

        for exp in exposures:
            c_comp = self.graph_engine.repo.get_company(exp.counterparty_id)
            if c_comp:
                c_keywords = self.SECTOR_KEYWORDS.get(c_comp.mainokved_code, [])
                if any(self._matches_keyword(kw, news_text) for kw in c_keywords):
                    affected_counterparties.append(exp)
                    weight = 10.0 if exp.risk_level == "HIGH" else (6.0 if exp.risk_level == "MEDIUM" else 3.0)
                    supply_chain_score = min(25.0, supply_chain_score + weight)

        # 5. Working Capital & Factoring Score (0 - 20 pts)
        wc_score = 0.0
        wc_matches = [kw for kw in self.WORKING_CAPITAL_KEYWORDS if self._matches_keyword(kw, news_text)]
        if wc_matches:
            if company.has_factoring or company.revenue_company >= 30_000_000_000.0:
                wc_score = min(20.0, 10.0 + len(wc_matches) * 3.0)

        # Role-based adjustments
        role_lower = role.lower()
        if "финанс" in role_lower or "cfo" in role_lower or "казначей" in role_lower:
            debt_score *= 1.15
            wc_score *= 1.15
        elif "бухгалтер" in role_lower:
            trade_score *= 1.15
        elif "генеральн" in role_lower or "директор" in role_lower or "собственник" in role_lower:
            direct_sector_score *= 1.15
            supply_chain_score *= 1.15

        raw_total = direct_sector_score + debt_score + trade_score + supply_chain_score + wc_score
        total_score = min(100.0, round(raw_total, 1))

        # Priority level classification
        if total_score >= 65.0:
            priority = "CRITICAL"
        elif total_score >= 45.0:
            priority = "HIGH"
        elif total_score >= 25.0:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Construct analytical explanation of the score
        reasons = []
        if direct_sector_score > 0:
            reasons.append(f"Прямое отраслевое совпадение с ОКВЭД {company.mainokved_code} ({company.mainokved_name})")
        if debt_score > 10.0:
            reasons.append("Высокая чувствительность к стоимости заемного капитала (наличие кредитного/лизингового портфеля)")
        if trade_score > 10.0:
            reasons.append(f"Экспортно-импортная экспозиция через базу ФТС ({company.fts_country_name or 'ВЭД'})")
        if affected_counterparties:
            names = ", ".join([cp.counterparty_name for cp in affected_counterparties[:2]])
            reasons.append(f"Связанный риск по ключевым контрагентам цепочки поставок: {names}")
        if wc_score > 5.0:
            reasons.append("Риск удлинения финансового цикла и дебиторской задолженности")

        explanation = "; ".join(reasons) if reasons else "Фоновое рыночное событие общего макроэкономического характера."

        return RelevanceScore(
            total_score=total_score,
            direct_sector_score=round(direct_sector_score, 1),
            debt_exposure_score=round(debt_score, 1),
            foreign_trade_score=round(trade_score, 1),
            counterparty_supply_chain_score=round(supply_chain_score, 1),
            working_capital_score=round(wc_score, 1),
            explanation=explanation,
            priority_level=priority,
        )
