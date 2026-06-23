import requests
import re
import logging
from bs4 import BeautifulSoup
from typing import List, Dict

logger = logging.getLogger(__name__)


class LiveSearch:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        try:
            encoded = requests.utils.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            for result in soup.select('.result')[:num_results]:
                title_el = result.select_one('.result__title a')
                snippet_el = result.select_one('.result__snippet')
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "url": title_el.get('href', ''),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    })
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def extract_text(self, url: str, max_chars: int = 2000) -> str:
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return ""
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            text = soup.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text[:max_chars]
        except Exception as e:
            logger.error(f"Extract error from {url}: {e}")
            return ""

    def get_evidence(self, query: str, max_sources: int = 3) -> str:
        results = self.search(query, num_results=max_sources)
        if not results:
            return ""

        evidence_parts = []
        for r in results:
            text = self.extract_text(r['url'])
            evidence_parts.append(
                f"Source: {r['title']}\n{r['url']}\n{text}\n"
            )

        return "\n===NEXT SOURCE===\n".join(evidence_parts)
