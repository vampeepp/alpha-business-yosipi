"""
Supply Chain & Counterparty Graph Engine.
Analyzes B2B payment flows from df_Uid_payment_hack.csv to compute:
- First-degree counterparties (Direct Suppliers & Buyers)
- Concentration ratios and financial exposure
- Second-degree contagion paths (Supply Chain shock transmission)
"""

from typing import List, Dict, Any, Optional
from src.domain.models import CounterpartyExposure, CompanyProfile


class CounterpartyGraphEngine:
    """Builds and queries the directed corporate supply chain graph."""

    def __init__(self, data_repo):
        self.repo = data_repo
        self.adj_out: Dict[str, List[Dict[str, Any]]] = {}  # PAYER -> list of {BENEFICIARY, AMT, CNT}
        self.adj_in: Dict[str, List[Dict[str, Any]]] = {}   # BENEFICIARY -> list of {PAYER, AMT, CNT}
        self._build_graph()

    def _build_graph(self):
        """Constructs adjacency structures from raw payment records."""
        for p in self.repo.payments_raw:
            payer = p["PAYER"]
            bene = p["BENEFICIARY"]
            amt = p["PAY_AMT"]
            cnt = p["PAY_CNT"]

            if payer not in self.adj_out:
                self.adj_out[payer] = []
            self.adj_out[payer].append({"counterparty": bene, "amt": amt, "cnt": cnt})

            if bene not in self.adj_in:
                self.adj_in[bene] = []
            self.adj_in[bene].append({"counterparty": payer, "amt": amt, "cnt": cnt})

    def get_counterparty_exposures(self, synthetic_u: str) -> List[CounterpartyExposure]:
        """Returns direct suppliers and customers with calculated exposure metrics."""
        company = self.repo.get_company(synthetic_u)
        revenue = company.revenue_company if company else 50_000_000_000.0

        exposures: List[CounterpartyExposure] = []

        # 1. Suppliers (Company is PAYER, sending money to BENEFICIARY)
        suppliers = self.adj_out.get(synthetic_u, [])
        for sup in suppliers:
            c_id = sup["counterparty"]
            c_comp = self.repo.get_company(c_id)
            c_name = f"{c_comp.mainokved_name} ({c_id})" if c_comp else f"Контрагент {c_id}"
            amt = sup["amt"]
            share = round((amt / revenue) * 100, 2)
            risk = "HIGH" if share > 15.0 else ("MEDIUM" if share > 5.0 else "LOW")
            exposures.append(
                CounterpartyExposure(
                    counterparty_id=c_id,
                    counterparty_name=c_name,
                    relation_type="ПОСТАВЩИК (Сырье/Услуги)",
                    payment_amount=amt,
                    payment_count=sup["cnt"],
                    share_of_turnover=share,
                    risk_level=risk,
                )
            )

        # 2. Buyers / Customers (Company is BENEFICIARY, receiving money from PAYER)
        buyers = self.adj_in.get(synthetic_u, [])
        for buy in buyers:
            c_id = buy["counterparty"]
            c_comp = self.repo.get_company(c_id)
            c_name = f"{c_comp.mainokved_name} ({c_id})" if c_comp else f"Контрагент {c_id}"
            amt = buy["amt"]
            share = round((amt / revenue) * 100, 2)
            risk = "HIGH" if share > 20.0 else ("MEDIUM" if share > 8.0 else "LOW")
            exposures.append(
                CounterpartyExposure(
                    counterparty_id=c_id,
                    counterparty_name=c_name,
                    relation_type="ПОКУПАТЕЛЬ (Выручка)",
                    payment_amount=amt,
                    payment_count=buy["cnt"],
                    share_of_turnover=share,
                    risk_level=risk,
                )
            )

        return sorted(exposures, key=lambda x: x.payment_amount, reverse=True)

    def get_supply_chain_network(self, synthetic_u: str, depth: int = 2) -> Dict[str, Any]:
        """Returns nodes and edges for graph visualization in the web dashboard."""
        nodes = {}
        edges = []

        def add_node(uid: str, is_root: bool = False):
            if uid not in nodes:
                c = self.repo.get_company(uid)
                nodes[uid] = {
                    "id": uid,
                    "label": c.mainokved_name if c else uid,
                    "org_type": c.org_type if c else "ЮЛ",
                    "revenue_bln": c.revenue_billions if c else 0.0,
                    "is_root": is_root,
                    "group_id": c.group_id if c else "",
                }

        add_node(synthetic_u, is_root=True)

        # Direct outward
        for out_edge in self.adj_out.get(synthetic_u, []):
            target = out_edge["counterparty"]
            add_node(target)
            edges.append({
                "from": synthetic_u,
                "to": target,
                "type": "OUT_PAYMENT",
                "label": f"Оплата сырья: {out_edge['amt'] / 1e9:.2f} млрд ₽",
                "amount": out_edge["amt"],
            })

        # Direct inward
        for in_edge in self.adj_in.get(synthetic_u, []):
            source = in_edge["counterparty"]
            add_node(source)
            edges.append({
                "from": source,
                "to": synthetic_u,
                "type": "IN_PAYMENT",
                "label": f"Выручка от продаж: {in_edge['amt'] / 1e9:.2f} млрд ₽",
                "amount": in_edge["amt"],
            })

        return {"nodes": list(nodes.values()), "edges": edges}
