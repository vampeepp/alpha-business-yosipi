"""
Domain Models for Alfa-Bank Corporate News Analytics & Insight Platform.
Implements data representations for Companies, Counterparty Supply Chains,
Alfa-Bank Macro Research, News Events, Relevance Scores, and 6-Pillar Insights.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class CompanyProfile:
    """Represents a corporate client matching df_Uid_data_hack.csv schema."""
    synthetic_u: str
    org_type: str
    okfs_name: str
    company_age_years: str
    eco_mark_label: str
    mainokved_code: str
    mainokved_name: str
    negative_mark: int
    workers_fns: str
    workers_spark: str
    cl_type: str
    has_rko: bool
    has_guarantee: bool
    has_loan: bool
    has_leasing: bool
    has_deposit: bool
    has_salary_project: bool
    fts_flag: bool
    fts_country_name: str
    has_factoring: bool
    revenue_company: float
    group_id: str
    city: str
    region: str

    @property
    def revenue_billions(self) -> float:
        """Returns annual revenue in billions of RUB."""
        return round(self.revenue_company / 1_000_000_000.0, 2)

    @property
    def is_large_enterprise(self) -> bool:
        """Checks if company meets > 15 billion RUB threshold (Slide 4)."""
        return self.revenue_company >= 15_000_000_000.0

    @property
    def has_foreign_trade(self) -> bool:
        """Checks if company engages in foreign trade customs operations."""
        return self.fts_flag or bool(self.fts_country_name)

    @property
    def is_debt_dependent(self) -> bool:
        """Checks if company relies on debt / bank credit facilities."""
        return self.has_loan or self.has_leasing

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["revenue_billions"] = self.revenue_billions
        res["is_large_enterprise"] = self.is_large_enterprise
        res["has_foreign_trade"] = self.has_foreign_trade
        res["is_debt_dependent"] = self.is_debt_dependent
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompanyProfile":
        return cls(
            synthetic_u=data.get("SYNTHETIC_U", data.get("synthetic_u", "")),
            org_type=data.get("ORG_TYPE", data.get("org_type", "")),
            okfs_name=data.get("OKFS_NAME", data.get("okfs_name", "")),
            company_age_years=data.get("COMPANY_AGE_YEARS_GRADATION", data.get("company_age_years", "")),
            eco_mark_label=data.get("ECO_MARK_LABEL", data.get("eco_mark_label", "")),
            mainokved_code=data.get("MAINOKVED_CODE", data.get("mainokved_code", "")),
            mainokved_name=data.get("MAINOKVED_NAME", data.get("mainokved_name", "")),
            negative_mark=int(data.get("NEGATIVEMARK", data.get("negative_mark", 0))),
            workers_fns=data.get("AMOUNT_WORKERS_FNS_GRADATION", data.get("workers_fns", "")),
            workers_spark=data.get("AMOUNT_WORKERS_SPARK_GRADATION", data.get("workers_spark", "")),
            cl_type=data.get("CL_TYPE", data.get("cl_type", "")),
            has_rko=bool(int(data.get("CL_PRODUCT_RKO_MARK", data.get("has_rko", 0)))),
            has_guarantee=bool(int(data.get("CL_PRODUCT_GAR_MARK", data.get("has_guarantee", 0)))),
            has_loan=bool(int(data.get("CL_PRODUCT_LOA_MARK", data.get("has_loan", 0)))),
            has_leasing=bool(int(data.get("CL_PRODUCT_LEA_MARK", data.get("has_leasing", 0)))),
            has_deposit=bool(int(data.get("CL_PRODUCT_DEP_MARK", data.get("has_deposit", 0)))),
            has_salary_project=bool(int(data.get("CL_PRODUCT_ZPP_MARK", data.get("has_salary_project", 0)))),
            fts_flag=bool(int(data.get("FTS_FLAG", data.get("fts_flag", 0)))),
            fts_country_name=data.get("FTS_COUNTRY_NAME", data.get("fts_country_name", "")),
            has_factoring=bool(int(data.get("FACTORING_MARK", data.get("has_factoring", 0)))),
            revenue_company=float(data.get("REVENUE_COMPANY", data.get("revenue_company", 0.0))),
            group_id=data.get("GROUP_ID", data.get("group_id", "")),
            city=data.get("CITY", data.get("city", "")),
            region=data.get("REGION", data.get("region", "")),
        )


@dataclass
class PhysicalPersonLink:
    """Maps linked physical persons / decision makers matching df_Fid_Uid_link_hack.csv."""
    synthetic_f: str
    city_name: str
    rc_name: str
    synthetic_u: str
    role_title: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CounterpartyExposure:
    """Represents a B2B counterparty exposure derived from df_Uid_payment_hack.csv."""
    counterparty_id: str
    counterparty_name: str
    relation_type: str  # "ПОСТАВЩИК" (Supplier) or "ПОКУПАТЕЛЬ" (Customer/Buyer)
    payment_amount: float
    payment_count: int
    share_of_turnover: float
    risk_level: str  # "LOW", "MEDIUM", "HIGH"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlfaMacroReport:
    """Represents Alfa-Bank Macro Research Report (Slide 17)."""
    id: str
    title: str
    date: str
    author: str
    summary: str
    full_text: str
    topics: List[str] = field(default_factory=list)
    impacted_sectors: List[str] = field(default_factory=list)
    key_indicators: Dict[str, str] = field(default_factory=dict)
    bank_recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImpactChainStep:
    """Represents a single causality step in the impact chain (Reviewer Criterion 7)."""
    step_title: str
    metric_affected: str  # "revenue", "margin", "liquidity", "supply", "capex"
    direction: str        # "UP", "DOWN", "NEUTRAL"
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImpactChain:
    """Full causal impact chain illustrating multi-order consequences (Reviewer Criterion 7)."""
    impact_strength: str  # "CRITICAL", "HIGH", "MODERATE"
    time_horizon: str     # "Краткосрочный (0-3 мес)", "Среднесрочный (3-12 мес)", "Долгосрочный (1+ год)"
    affected_dimensions: List[str]  # ["revenue", "margin", "liquidity", "supply"]
    steps: List[ImpactChainStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "impact_strength": self.impact_strength,
            "time_horizon": self.time_horizon,
            "affected_dimensions": self.affected_dimensions,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class NewsItem:
    """Represents an external news article or market event."""
    news_id: str
    title: str
    publication_date: str
    source: str
    summary: str
    full_content: str
    category: str
    entities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    urgency: str = "MEDIUM"
    sentiment: str = "NEUTRAL"
    novelty_score: float = 90.0
    cross_verification_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RelevanceScore:
    """Breakdown of personalized relevance scoring for a company-news pair."""
    total_score: float
    direct_sector_score: float
    debt_exposure_score: float
    foreign_trade_score: float
    counterparty_supply_chain_score: float
    working_capital_score: float
    explanation: str
    priority_level: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PersonalizedInsight:
    """Comprehensive 6-Pillar Insight with Impact Chain and FACT->RESEARCH->INSIGHT matrix."""
    what_happened: str
    why_it_matters: str
    potential_consequences: str
    recommended_actions: str
    bank_expert_perspective: str
    data_lineage: Dict[str, Any]
    impact_chain: Optional[ImpactChain] = None
    fact_to_insight_matrix: Dict[str, Any] = field(default_factory=dict)
    novelty_score: float = 92.0
    cross_verification_score: float = 95.0
    suggested_bank_products: List[Dict[str, str]] = field(default_factory=list)
    agent_confidence: float = 0.95
    critic_review: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.impact_chain:
            res["impact_chain"] = self.impact_chain.to_dict()
        return res


@dataclass
class AgentTraceStep:
    """Represents an observable trace step in the multi-step agentic lifecycle (Slide 7, 10)."""
    step_number: int
    step_name: str
    agent_role: str
    action_summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
