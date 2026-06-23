import json
import logging
from typing import List, Dict, Tuple
from backend.database import Database
from backend.embeddings import EmbeddingIndex
from backend.config import SIMILARITY_THRESHOLD, TOP_K

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self):
        self.db = Database()
        self.embeddings = EmbeddingIndex()
        loaded = self.embeddings.load()
        if not loaded:
            logger.info("No existing FAISS index found. Will build on ingestion.")

    def search(self, query: str, year: int = None) -> List[Dict]:
        seen_ids = set()
        combined = []

        semantic_results = self.embeddings.search(query, k=TOP_K)
        for event_id, score in semantic_results:
            if score >= SIMILARITY_THRESHOLD and event_id not in seen_ids:
                seen_ids.add(event_id)
                event = self.db.get_event(event_id)
                if event:
                    event['_score'] = score
                    event['_match_type'] = 'semantic'
                    combined.append(event)

        keyword_results = self.db.search_by_keyword(query, year=year, limit=TOP_K)
        for row in keyword_results:
            if row['id'] not in seen_ids:
                seen_ids.add(row['id'])
                row['_score'] = 0.5
                row['_match_type'] = 'keyword'
                combined.append(row)

        combined.sort(key=lambda x: x.get('_score', 0), reverse=True)
        return combined[:TOP_K]

    def get_context(self, query: str, year: int = None) -> Tuple[str, List[Dict]]:
        events = self.search(query, year)
        if not events:
            return "", []

        context_parts = []
        for e in events:
            sources = e.get('sources', '[]')
            if isinstance(sources, str):
                sources_list = json.loads(sources)
            else:
                sources_list = sources

            keywords = e.get('keywords', '[]')
            if isinstance(keywords, str):
                kw_list = json.loads(keywords)
            else:
                kw_list = keywords

            context_parts.append(
                f"Event: {e['title']}\n"
                f"Summary: {e['summary']}\n"
                f"Year: {e['year']}\n"
                f"Category: {e['category']}\n"
                f"Sources: {', '.join(sources_list)}\n"
                f"Keywords: {', '.join(kw_list)}\n"
            )

        context = "\n---\n".join(context_parts)
        return context, events

    @property
    def is_available(self) -> bool:
        return self.embeddings.size > 0
