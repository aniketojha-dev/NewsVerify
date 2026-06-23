import feedparser
import requests
import re
import logging
from typing import List, Dict

from backend.config import RSS_SOURCES

logger = logging.getLogger(__name__)


class RSSIngestion:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_feed(self, url: str, max_entries: int = 50) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(url)
            entries = feed.entries[:max_entries]
            source_title = feed.feed.get("title", "Unknown")

            for entry in entries:
                description = entry.get("summary", "") or entry.get("description", "")
                description = re.sub(r'<[^>]+>', '', description)

                articles.append({
                    "title": entry.get("title", ""),
                    "description": description,
                    "url": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": source_title,
                })

            logger.info(f"Fetched {len(articles)} from {url[:60]}...")
        except Exception as e:
            logger.error(f"Feed error {url[:60]}: {e}")

        return articles

    def _search_google_news(self, query: str, max_entries: int = 20) -> List[Dict]:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        articles = self.fetch_feed(url, max_entries)
        for a in articles:
            a["_source_name"] = f"Google News Search: {query}"
        return articles

    def fetch_all(self, max_per_source: int = 50) -> List[Dict]:
        all_articles = []

        for source_name, url in RSS_SOURCES.items():
            articles = self.fetch_feed(url, max_per_source)
            for a in articles:
                a["_source_name"] = source_name
            all_articles.extend(articles)

        year_queries = []
        for year in [2025, 2026]:
            year_queries.extend([
                f"{year}",
                f"{year} India",
                f"{year} technology",
                f"{year} sports",
                f"{year} business",
                f"{year} politics",
                f"{year} science",
                f"{year} world news",
            ])
            for month in range(1, 13):
                month_str = f"{year}-{month:02d}"
                year_queries.append(month_str)

        for q in year_queries:
            articles = self._search_google_news(q, 20)
            all_articles.extend(articles)

        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles
