import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from backend.database import Database

    db = Database()
    count = db.count_events()
    logger.info(f"Database has {count} events")

    if count == 0:
        logger.info("No events in database. Starting ingestion...")
        from backend.ingest import run_ingestion
        run_ingestion()
        count = db.count_events()
        logger.info(f"Database now has {count} events")

    import uvicorn
    logger.info("Starting NewsVerify AI server at http://localhost:8000")
    logger.info("Open frontend at http://localhost:3000 (run: cd frontend && npm run dev)")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
