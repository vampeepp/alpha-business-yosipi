"""
Main application entry point for Alfa-Bank Corporate News Analytics.
Supports starting the web server or running automated verification runs.
"""

import sys
import argparse
import logging
from src.config import SERVER_HOST, SERVER_PORT
from src.web.server import run_server

logger = logging.getLogger("AlfaNewsAnalytics.Main")


def main():
    parser = argparse.ArgumentParser(description="Alfa-Bank Corporate News Analytics & Insight Platform")
    parser.add_argument("--host", default=SERVER_HOST, help="Host address to bind HTTP server")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="Port for HTTP server")
    parser.add_argument("--verify", action="store_true", help="Run automated end-to-end verification and exit")

    args = parser.parse_args()

    if args.verify:
        from tests.test_e2e import run_verification_suite
        success = run_verification_suite()
        sys.exit(0 if success else 1)

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
