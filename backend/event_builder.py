import re
import json
import sqlite3
import logging
import numpy as np
from typing import List, Dict
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.database import Database
from backend.embeddings import EmbeddingIndex
from backend.config import DATABASE_PATH, CLUSTER_THRESHOLD

logger = logging.getLogger(__name__)


class EventBuilder:
    def __init__(self):
        self.db = Database()
        self.embeddings = EmbeddingIndex()
        self.embeddings.load()

    def _infer_category(self, article: Dict) -> str:
        text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        categories = {
            'Technology': ['ai', 'artificial intelligence', 'technology', 'digital', 'software',
                           'computer', 'cyber', 'tech', 'startup', 'app', 'data', 'robot', 'chip',
                           'algorithm', 'automation', 'quantum', 'blockchain', 'gpu', 'model'],
            'Sports': ['sports', 'cricket', 'football', 'soccer', 'tennis', 'olympic',
                       'champions', 'league', 'tournament', 'match', 'player', 'coach',
                       'goal', 'medal', 'stadium', 'athlete', 'final', 'championship', 'ipl'],
            'Business': ['business', 'market', 'stock', 'economy', 'finance', 'bank',
                         'trade', 'investment', 'economic', 'corporate', 'merger',
                         'acquisition', 'profit', 'revenue', 'ipo', 'funding', 'startup',
                         'ceo', 'company', 'budget', 'gdp'],
            'Politics': ['politics', 'government', 'election', 'minister', 'president',
                         'parliament', 'congress', 'democratic', 'republican', 'political',
                         'vote', 'policy', 'law', 'legislation', 'senate', 'bill',
                         'modi', 'trump', 'biden', 'pm', 'mp'],
            'Science': ['science', 'research', 'study', 'space', 'nasa', 'climate',
                        'environment', 'medical', 'health', 'gene', 'dna', 'physics',
                        'biology', 'chemistry', 'astronomy', 'discovery', 'vaccine',
                        'nuclear', 'quantum', 'lab'],
            'World News': ['world', 'international', 'global', 'foreign', 'war',
                           'conflict', 'treaty', 'diplomat', 'united nations', 'china',
                           'russia', 'ukraine', 'middle east', 'europe', 'africa',
                           'asia', 'america', 'border', 'sanction', 'nato', 'un'],
        }
        scores = {cat: sum(1 for kw in kws if kw in text) for cat, kws in categories.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'Miscellaneous'

    def _extract_year(self, article: Dict) -> int:
        text = article.get('title', '') + ' ' + article.get('description', '')
        years = re.findall(r'\b(202[5-6])\b', text)
        if years:
            return int(years[0])
        try:
            from dateutil import parser
            dt = parser.parse(article.get('published', ''))
            if 2025 <= dt.year <= 2026:
                return dt.year
        except Exception:
            pass
        return 2025

    def _extract_keywords(self, text: str, max_keywords: int = 8) -> List[str]:
        stops = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
                 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'shall', 'can', 'need',
                 'this', 'that', 'these', 'those', 'it', 'its', 'he', 'she', 'they',
                 'them', 'their', 'his', 'her', 'what', 'which', 'who', 'whom',
                 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
                 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'because',
                 'has', 'get', 'new', 'after', 'before', 'about', 'into', 'over',
                 'also', 'now', 'then', 'here', 'there', 'up', 'down', 'out', 'off',
                 'well', 'back', 'much', 'still', 'yet', 'already', 'while', 'since',
                 'until', 'if', 'though', 'although', 'even', 'any', 'many'}
        text = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', text)
        words = [w for w in words if w not in stops]
        return [w for w, _ in Counter(words).most_common(max_keywords)]

    def _cluster_articles_vectorized(self, articles: List[Dict]) -> List[List[Dict]]:
        if not articles:
            return []

        texts = []
        valid_articles = []
        for a in articles:
            t = (a.get('title', '') + ' ' + a.get('description', '')).strip()
            if t:
                texts.append(t)
                valid_articles.append(a)

        if len(texts) < 2:
            return [[a] for a in valid_articles]

        vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        tfidf = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf)

        assigned = [False] * len(valid_articles)
        clusters = []

        for i in range(len(valid_articles)):
            if assigned[i]:
                continue
            cluster = [valid_articles[i]]
            assigned[i] = True
            for j in range(i + 1, len(valid_articles)):
                if not assigned[j] and sim_matrix[i, j] >= CLUSTER_THRESHOLD:
                    cluster.append(valid_articles[j])
                    assigned[j] = True
            clusters.append(cluster)

        return clusters

    def _build_event(self, cluster: List[Dict]) -> Dict:
        titles = [a.get('title', '') for a in cluster if a.get('title')]
        descriptions = [a.get('description', '') for a in cluster if a.get('description')]
        sources = list(set(a.get('_source_name', '') for a in cluster if a.get('_source_name')))
        urls = [a.get('url', '') for a in cluster if a.get('url')]

        best_title = Counter(titles).most_common(1)[0][0] if titles else "Unknown Event"
        summary = ' '.join(descriptions[:3]) if descriptions else best_title
        if len(summary) > 1000:
            summary = summary[:997] + '...'

        years = [self._extract_year(a) for a in cluster]
        year = Counter(years).most_common(1)[0][0]
        categories = [self._infer_category(a) for a in cluster]
        category = Counter(categories).most_common(1)[0][0]
        keywords = self._extract_keywords(' '.join(titles + descriptions))

        return {
            'title': best_title,
            'summary': summary,
            'year': year,
            'category': category,
            'sources': sources,
            'keywords': keywords,
            'url': urls[0] if urls else None,
        }

    def _event_exists(self, title: str) -> bool:
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            rows = conn.execute("SELECT title FROM events").fetchall()
            conn.close()
            if not rows:
                return False
            existing = [r[0] for r in rows]
            vectorizer = TfidfVectorizer(stop_words='english')
            all_texts = existing + [title]
            tfidf = vectorizer.fit_transform(all_texts)
            sims = cosine_similarity(tfidf[-1:], tfidf[:-1])[0]
            return bool(np.any(sims > 0.92))
        except Exception:
            return False

    def process_articles(self, articles: List[Dict]) -> int:
        logger.info(f"Processing {len(articles)} articles into events...")

        seen_urls = set()
        unique = []
        for a in articles:
            url = a.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(a)
            elif not url:
                unique.append(a)

        logger.info(f"Deduplicated to {len(unique)} unique articles by URL")

        clusters = self._cluster_articles_vectorized(unique)
        logger.info(f"Formed {len(clusters)} clusters from {len(unique)} articles")

        event_count = 0
        for cluster in clusters:
            if not cluster:
                continue
            event = self._build_event(cluster)
            if event['year'] not in {2025, 2026}:
                continue
            if self._event_exists(event['title']):
                continue

            event_id = self.db.add_event(
                title=event['title'],
                summary=event['summary'],
                year=event['year'],
                category=event['category'],
                sources=event['sources'],
                keywords=event['keywords'],
                url=event['url'],
            )
            event_text = f"{event['title']} {event['summary']} {' '.join(event['keywords'])}"
            self.embeddings.add_to_index(event_id, event_text)
            event_count += 1

        self.embeddings._save()
        logger.info(f"Built {event_count} new events")
        return event_count
