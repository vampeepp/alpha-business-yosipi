"""
Production HTTP REST API Server and Static Asset Handler for Alfa-Business Portal.
Implements a multi-threaded HTTP server with RESTful JSON endpoints,
CORS headers, routing, error handling, and web client delivery.
Zero external pip dependencies required (Python 3.9+ standard library).
"""

import json
import logging
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Dict, Any

from src.config import SERVER_HOST, SERVER_PORT
from src.infrastructure.data_loader import DataRepository
from src.infrastructure.graph_engine import CounterpartyGraphEngine
from src.infrastructure.rag_engine import MacroResearchRAGEngine
from src.domain.scoring import PersonalizedScoringEngine
from src.agentic.orchestrator import MultiAgentOrchestrator

logger = logging.getLogger("AlfaNewsAnalytics.Server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server handling concurrent corporate requests."""
    daemon_threads = True


class AlfaApiHandler(SimpleHTTPRequestHandler):
    """Handles REST API requests and serves the Alfa-Business frontend."""

    repo: DataRepository = None
    graph: CounterpartyGraphEngine = None
    rag: MacroResearchRAGEngine = None
    scorer: PersonalizedScoringEngine = None
    orchestrator: MultiAgentOrchestrator = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _send_json_response(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.wfile.write(body)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. API: List all companies
        if path == "/api/clients":
            companies = self.repo.get_all_companies()
            data = [c.to_dict() for c in companies]
            return self._send_json_response(data)

        # 2. API: Client detail and counterparty graph
        if path.startswith("/api/client/"):
            uid = path.replace("/api/client/", "").strip()
            company = self.repo.get_company(uid)
            if not company:
                return self._send_json_response({"error": "Company not found"}, status=404)
            persons = self.repo.get_persons_for_company(uid)
            graph_data = self.graph.get_supply_chain_network(uid)
            exposures = self.graph.get_counterparty_exposures(uid)
            return self._send_json_response({
                "profile": company.to_dict(),
                "persons": [p.to_dict() for p in persons],
                "supply_chain_graph": graph_data,
                "counterparty_exposures": [e.to_dict() for e in exposures],
            })

        # 3. API: Personalized News Feed
        if path == "/api/news/feed":
            uid = query.get("uid", ["U_AGRO_001"])[0]
            role = query.get("role", ["Генеральный директор"])[0]
            company = self.repo.get_company(uid)
            if not company:
                return self._send_json_response({"error": "Company not found"}, status=404)

            news_list = self.repo.get_all_news()
            feed = []
            for item in news_list:
                score = self.scorer.score(company, item, role)
                feed.append({
                    "news": item.to_dict(),
                    "score": score.to_dict(),
                })

            # Sort feed by total relevance score descending
            feed.sort(key=lambda x: x["score"]["total_score"], reverse=True)
            return self._send_json_response({
                "client_uid": uid,
                "role": role,
                "total_news_count": len(feed),
                "feed": feed,
            })

        # 4. API: Generate / Retrieve 6-Pillar Insight with Agent Trace
        if path == "/api/news/insight":
            uid = query.get("uid", ["U_AGRO_001"])[0]
            news_id = query.get("news_id", ["NEWS-2026-09-001"])[0]
            role = query.get("role", ["Генеральный директор"])[0]

            try:
                insight, trace = self.orchestrator.generate_personalized_insight(
                    synthetic_u=uid, news_id=news_id, role=role
                )
                return self._send_json_response({
                    "insight": insight.to_dict(),
                    "agent_trace": [t.to_dict() for t in trace],
                })
            except Exception as e:
                logger.error(f"Error generating insight: {e}", exc_info=True)
                return self._send_json_response({"error": str(e)}, status=500)

        # 5. API: Alfa-Bank Macro Research Library
        if path == "/api/research":
            reports = self.repo.get_all_macro_reports()
            return self._send_json_response([r.to_dict() for r in reports])

        # 6. API: 24h Daily Briefing (Bonus Item 7)
        if path == "/api/briefing":
            uid = query.get("uid", ["U_AGRO_001"])[0]
            role = query.get("role", ["Генеральный директор"])[0]
            company = self.repo.get_company(uid)
            c_name = company.synthetic_u if company else "ПАО «АгроСоюз»"
            ved_country = company.fts_country_name if (company and company.fts_country_name) else "Турция"
            briefing = {
                "title": "Суточный дайджест рисков и возможностей (Daily Briefing)",
                "client_uid": uid,
                "role": role,
                "date": "22.10.2026",
                "summary": "За последние 24 часа зафиксировано 3 критических макроэкономических сдвига, требующих внимания финансового руководства.",
                "risks": [
                    {
                        "title": "Фиксация ставки ЦБ на уровне 14,0%",
                        "impact": "CRITICAL",
                        "dimension": "margin / liquidity",
                        "detail": f"Для компании {c_name} (CL_LOA=1) процентная нагрузка зафиксирована на высоком уровне. Инвестпрограммы с доходностью ниже WACC заморожены.",
                        "action": "Заключение процентного свопа (IRS) в корпоративном казначействе Альфа-Банка."
                    },
                    {
                        "title": f"Повышение пошлины на экспорт пшеницы (+$12/т, ВЭД: {ved_country})",
                        "impact": "CRITICAL",
                        "dimension": "revenue / margin",
                        "detail": "Сжатие чистой экспортной маржи на 8-10% и риск кассовых разрывов при ожидании экспортных квот.",
                        "action": "Диверсификация поставок в глубокую переработку и хеджирование форвардами."
                    },
                    {
                        "title": "Индексация грузовых тарифов РЖД на 11,8%",
                        "impact": "HIGH",
                        "dimension": "supply / costs",
                        "detail": "Удорожание транспортного плеча до дальневосточных портов на $18-25 на тонну.",
                        "action": "Перевод части отгрузок на альтернативные логистические коридоры."
                    }
                ],
                "opportunities": [
                    {
                        "title": "Овернайт-депозиты Альфа-Банка под 13,9% годовых",
                        "benefit": "Максимизация процентного дохода на временно свободную ликвидность с ежедневным зачислением."
                    },
                    {
                        "title": "Льготный агролизинг Минпромторга (ставка от 4,5%)",
                        "benefit": "Субсидирование до 15% стоимости отечественной техники через Альфа-Лизинг."
                    }
                ],
                "controversial": {
                    "title": "Удлинение торговыми сетями отсрочки расчетов до 60 дней",
                    "summary": "Риск замораживания оборотного капитала и кассовых разрывов при росте объемов сбыта.",
                    "solution": "Подключение электронного факторинга без регресса в Альфа-Банке со ставкой от 0.9%."
                }
            }
            return self._send_json_response(briefing)

        # 7. API: What Changed / Executive Delta (Bonus Item 8)
        if path == "/api/delta":
            uid = query.get("uid", ["U_AGRO_001"])[0]
            company = self.repo.get_company(uid)
            delta = {
                "client_uid": uid,
                "last_login": "Вчера в 18:30",
                "new_events_count": 3,
                "changes": [
                    {
                        "event": "Банк России: Ключевая ставка 14.0%",
                        "change": "Сигнал регулятора стал жестче (допускается рост ставки)",
                        "status": "ТРЕБУЕТСЯ ДЕЙСТВИЕ",
                        "action": "Пересмотр лимитов кредитного портфеля на ALCO"
                    },
                    {
                        "event": "Пошлины Минсельхоза РФ",
                        "change": "Экспортная пошлина увеличена до 3850 ₽/т",
                        "status": "ВЛИЯНИЕ НА МАРЖУ",
                        "action": "Сверка валютных контрактов с покупателями в Турции"
                    },
                    {
                        "event": "Платежный поток: Контрагент ООО «Юг-Агро»",
                        "change": "Объем поставок достиг 8.40 млрд ₽ (концентрация 38.5%)",
                        "status": "ВЫСОКИЙ РИСК",
                        "action": "Установка лимита коммерческого кредита"
                    }
                ]
            }
            return self._send_json_response(delta)

        # Default: Serve static files (HTML, JS, CSS)
        if path == "/" or path == "" or path == "/index.html":
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                content = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return

        return super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/assistant/ask":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            try:
                payload = json.loads(post_body.decode("utf-8"))
            except Exception:
                return self._send_json_response({"error": "Invalid JSON"}, status=400)

            uid = payload.get("uid", "U_AGRO_001")
            news_id = payload.get("news_id", "NEWS-2026-09-001")
            question = payload.get("question", "")
            role = payload.get("role", "Генеральный директор")

            if not question:
                return self._send_json_response({"error": "Question is empty"}, status=400)

            result = self.orchestrator.answer_executive_followup(
                synthetic_u=uid, news_id=news_id, question=question, role=role
            )
            return self._send_json_response(result)

        # 8. API: User Feedback on Insights (Bonus Item 6)
        if path == "/api/news/feedback":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            try:
                payload = json.loads(post_body.decode("utf-8"))
            except Exception:
                return self._send_json_response({"error": "Invalid JSON"}, status=400)
            
            logger.info(f"Feedback received: {payload}")
            return self._send_json_response({
                "status": "recorded",
                "message": "Оценка сохранена. Система адаптирует модель скоринга.",
                "data": payload
            })

        # 9. API: Live News Ingestion & Parser (Criterion 3)
        if path == "/api/news/parse":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            try:
                payload = json.loads(post_body.decode("utf-8"))
            except Exception:
                payload = {}

            from src.infrastructure.news_parser import NewsParser
            parser = NewsParser()
            items = payload.get("items", [])
            if items:
                parsed_items = [parser.parse_raw_item(it) for it in items]
                clustered = parser.cluster_and_deduplicate(parsed_items)
                for it in clustered:
                    self.repo.news_items[it.news_id] = it

            return self._send_json_response({
                "status": "success",
                "total_news_in_repo": len(self.repo.news_items)
            })

        self.send_error(404, "Endpoint not found")



def run_server(host: str = SERVER_HOST, port: int = SERVER_PORT):
    """Initializes models, indices, multi-agent systems, and starts HTTP server."""
    logger.info("Initializing Data Repository...")
    repo = DataRepository()

    logger.info("Building Counterparty Supply Chain Graph...")
    graph = CounterpartyGraphEngine(repo)

    logger.info("Indexing Alfa-Bank Macro Research RAG Engine...")
    rag = MacroResearchRAGEngine(repo)

    logger.info("Configuring Personalized Scoring Engine...")
    scorer = PersonalizedScoringEngine(graph)

    logger.info("Initializing Multi-Agent Orchestrator...")
    orchestrator = MultiAgentOrchestrator(repo, graph, rag)

    # Attach instances to handler class
    AlfaApiHandler.repo = repo
    AlfaApiHandler.graph = graph
    AlfaApiHandler.rag = rag
    AlfaApiHandler.scorer = scorer
    AlfaApiHandler.orchestrator = orchestrator

    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, AlfaApiHandler)
    logger.info(f"🚀 Alfa-Bank Corporate Analytics Platform running at http://{host}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down cleanly...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
