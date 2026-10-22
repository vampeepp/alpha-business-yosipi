"""
Data loader and repository module.
Loads, validates, and indexes Hackathon datasets:
- df_Uid_data_hack.csv
- df_Fid_Uid_link_hack.csv
- df_Uid_payment_hack.csv
- alfa_macro_research.json
- external_news_stream.json
"""

import csv
import json
import logging
from typing import Dict, List, Optional, Any
from src.config import (
    CLIENT_DATA_CSV,
    PERSONS_DATA_CSV,
    PAYMENTS_DATA_CSV,
    ALFA_MACRO_RESEARCH_JSON,
    EXTERNAL_NEWS_JSON,
)
from src.domain.models import (
    CompanyProfile,
    PhysicalPersonLink,
    AlfaMacroReport,
    NewsItem,
)

logger = logging.getLogger("AlfaNewsAnalytics.DataLoader")


class DataRepository:
    """Central in-memory store for corporate clients, relations, macro research, and news."""

    def __init__(self):
        self.companies: Dict[str, CompanyProfile] = {}
        self.persons: List[PhysicalPersonLink] = []
        self.payments_raw: List[Dict[str, Any]] = []
        self.macro_reports: Dict[str, AlfaMacroReport] = {}
        self.news_items: Dict[str, NewsItem] = {}
        self.load_all()

    def load_all(self):
        """Loads all datasets from disk."""
        self._load_companies()
        self._load_persons()
        self._load_payments()
        self._load_macro_research()
        self._load_news()
        logger.info(
            f"Successfully loaded {len(self.companies)} companies, {len(self.persons)} persons, "
            f"{len(self.payments_raw)} payment links, {len(self.macro_reports)} macro reports, "
            f"{len(self.news_items)} news items."
        )

    def _load_companies(self):
        if not CLIENT_DATA_CSV.exists():
            logger.error(f"Client CSV file missing: {CLIENT_DATA_CSV}")
            return
        with open(CLIENT_DATA_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                profile = CompanyProfile.from_dict(row)
                self.companies[profile.synthetic_u] = profile

    def _load_persons(self):
        if not PERSONS_DATA_CSV.exists():
            return
        with open(PERSONS_DATA_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.persons.append(
                    PhysicalPersonLink(
                        synthetic_f=row.get("SYNTHETIC_F", ""),
                        city_name=row.get("CITY_NAME", ""),
                        rc_name=row.get("RC_NAME", ""),
                        synthetic_u=row.get("SYNTHETIC_U", ""),
                        role_title=row.get("ROLE_TITLE", "Менеджер"),
                    )
                )

    def _load_payments(self):
        if not PAYMENTS_DATA_CSV.exists():
            return
        with open(PAYMENTS_DATA_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.payments_raw.append({
                    "BENEFICIARY": row.get("BENEFICIARY", "").strip(),
                    "PAYER": row.get("PAYER", "").strip(),
                    "PAY_AMT": float(row.get("PAY_AMT", 0.0)),
                    "PAY_CNT": int(row.get("PAY_CNT", 0)),
                })

    def _load_macro_research(self):
        if not ALFA_MACRO_RESEARCH_JSON.exists():
            return
        with open(ALFA_MACRO_RESEARCH_JSON, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                report = AlfaMacroReport(
                    id=item.get("id"),
                    title=item.get("title"),
                    date=item.get("date"),
                    author=item.get("author"),
                    summary=item.get("summary"),
                    full_text=item.get("full_text"),
                    topics=item.get("topics", []),
                    impacted_sectors=item.get("impacted_sectors", []),
                    key_indicators=item.get("key_indicators", {}),
                    bank_recommendations=item.get("bank_recommendations", []),
                )
                self.macro_reports[report.id] = report

    def _load_news(self):
        if not EXTERNAL_NEWS_JSON.exists():
            return
        with open(EXTERNAL_NEWS_JSON, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                news = NewsItem(
                    news_id=item.get("news_id"),
                    title=item.get("title"),
                    publication_date=item.get("publication_date"),
                    source=item.get("source"),
                    summary=item.get("summary"),
                    full_content=item.get("full_content"),
                    category=item.get("category"),
                    entities=item.get("entities", []),
                    tags=item.get("tags", []),
                    urgency=item.get("urgency", "MEDIUM"),
                    sentiment=item.get("sentiment", "NEUTRAL"),
                )
                self.news_items[news.news_id] = news

    def get_company(self, synthetic_u: str) -> Optional[CompanyProfile]:
        return self.companies.get(synthetic_u)

    def get_persons_for_company(self, synthetic_u: str) -> List[PhysicalPersonLink]:
        return [p for p in self.persons if p.synthetic_u == synthetic_u]

    def get_all_companies(self) -> List[CompanyProfile]:
        return list(self.companies.values())

    def get_all_news(self) -> List[NewsItem]:
        return list(self.news_items.values())

    def get_all_macro_reports(self) -> List[AlfaMacroReport]:
        return list(self.macro_reports.values())
