"""
Hybrid RAG Engine for Alfa-Bank Macroeconomic Research.
Implements lexical (BM25/TF-IDF) and topical semantic matching across
Alfa-Bank internal research publications and market event streams.
Preserves strict source citation and provenance (Slide 9, 13).
"""

import re
import math
from typing import List, Dict, Any, Tuple
from collections import Counter
from src.domain.models import AlfaMacroReport, NewsItem


class MacroResearchRAGEngine:
    """Retrieves relevant Alfa-Bank macro research papers matching query & context."""

    def __init__(self, data_repo):
        self.repo = data_repo
        self.reports: List[AlfaMacroReport] = data_repo.get_all_macro_reports()
        self.corpus_tokens: Dict[str, List[str]] = {}
        self.doc_freq: Counter = Counter()
        self._index_corpus()

    def _tokenize(self, text: str) -> List[str]:
        """Cleans and extracts Russian/English normalized tokens."""
        text = text.lower()
        tokens = re.findall(r"[a-zа-яё0-9]{3,}", text)
        return tokens

    def _index_corpus(self):
        """Builds in-memory inverted document index."""
        for report in self.reports:
            full_content = f"{report.title} {report.summary} {report.full_text} {' '.join(report.topics)} {' '.join(report.impacted_sectors)}"
            tokens = self._tokenize(full_content)
            self.corpus_tokens[report.id] = tokens
            unique_terms = set(tokens)
            for t in unique_terms:
                self.doc_freq[t] += 1

    def retrieve(self, query: str, sector: str = "", top_k: int = 3) -> List[Tuple[AlfaMacroReport, float, str]]:
        """
        Retrieves top_k most relevant Alfa-Bank macro research reports.
        Returns: List of (Report, RelevanceScore, MatchedPassageSummary)
        """
        query_tokens = self._tokenize(query)
        if sector:
            query_tokens.extend(self._tokenize(sector))

        scores: List[Tuple[AlfaMacroReport, float, str]] = []
        num_docs = max(len(self.reports), 1)

        for report in self.reports:
            doc_tokens = self.corpus_tokens.get(report.id, [])
            doc_len = len(doc_tokens)
            if doc_len == 0:
                continue

            tf = Counter(doc_tokens)
            score = 0.0

            for q in query_tokens:
                if q in tf:
                    # BM25-style weighting
                    idf = math.log((num_docs - self.doc_freq[q] + 0.5) / (self.doc_freq[q] + 0.5) + 1.0)
                    term_freq = tf[q]
                    score += idf * ((term_freq * 2.2) / (term_freq + 1.2 * (0.25 + 0.75 * doc_len / 150.0)))

            # Sector & Topic boost
            if sector:
                for imp_sec in report.impacted_sectors:
                    if sector.lower() in imp_sec.lower() or imp_sec.lower() in sector.lower():
                        score += 5.0
            for topic in report.topics:
                if any(q in topic.lower() for q in query_tokens):
                    score += 3.0

            if score > 0:
                passage = report.summary[:240] + "..." if len(report.summary) > 240 else report.summary
                scores.append((report, round(score, 2), passage))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
