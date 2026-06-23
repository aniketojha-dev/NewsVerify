import logging
import sys

from backend.rss_ingestion import RSSIngestion
from backend.event_builder import EventBuilder
from backend.database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_ingestion():
    logger.info("=" * 50)
    logger.info("NewsVerify AI - Data Ingestion")
    logger.info("=" * 50)

    rss = RSSIngestion()
    articles = rss.fetch_all(max_per_source=50)
    logger.info(f"Total articles fetched: {len(articles)}")

    if not articles:
        logger.warning("No articles fetched. Check network.")
        return 0

    builder = EventBuilder()
    count = builder.process_articles(articles)

    db = Database()
    logger.info(f"\nTotal events: {db.count_events()}")
    cats = db.count_by_category()
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        logger.info(f"  {cat}: {cnt}")

    return count


if __name__ == "__main__":
    count = run_ingestion()
    print(f"\n{'=' * 50}")
    print(f"Ingestion complete: {count} events added")
    print(f"{'=' * 50}")
