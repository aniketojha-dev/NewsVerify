import json
import logging
import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.models import QueryRequest, QueryResponse, KeyDetail
from backend.year_detector import detect_year
from backend.retriever import Retriever
from backend.openrouter_client import OpenRouterClient
from backend.live_search import LiveSearch
from backend.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NewsVerify", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



retriever = Retriever()
llm = OpenRouterClient()
live_search = LiveSearch()
db = Database()

SYSTEM_PROMPT = """You are NewsVerify. Verify news events from 2025-2026 using ONLY the context below.

Output (max 150 words):
Summary: 1-2 sentences answering the question.
Key Facts: Bullet points — dates, locations, outcomes, casualties.
Sources: Named sources from the context.

Rules: No markdown, no prefixes like "Short Answer:". No made-up facts. If context lacks info, say so.

Context:"""

LIVE_SYSTEM_PROMPT = """You are NewsVerify. Analyze live search results to answer news queries.

Output (max 150 words):
Summary: 1-2 sentences.
Key Facts: Bullet points with dates, locations, outcomes.
Sources: Named sources from the results.

Rules: No markdown, no prefixes. If insufficient info, say so.

Search Results:"""


def _compute_confidence(event, result, source_type):
    if not source_type:
        return 0, "Not Found"

    if source_type == "local":
        score = event.get('_score', 0.75) if event else 0.75
        base = max(65, int(score * 88))
        sources_raw = event.get('sources', '[]')
        sources_list = json.loads(sources_raw) if isinstance(sources_raw, str) else sources_raw
        boost = min(20, len(sources_list) * 4)
        llm_boost = 8 if result and result.get("success") else 0
        final_score = min(99, base + boost + llm_boost)
        if final_score >= 88:
            status = "Verified"
        elif final_score >= 72:
            status = "Likely Verified"
        else:
            status = "Plausible"
        return final_score, status

    if source_type == "live":
        live_boost = 8 if result and result.get("success") else 0
        return min(85, 68 + live_boost), "Live Sourced"

    if result and result.get("success"):
        return 55, "Generated"

    return 0, "Not Found"


def _extract_key_details(answer_text, event):
    details = []
    if event:
        year = event.get('year')
        if year:
            details.append(KeyDetail(label="Year", value=str(year)))
        category = event.get('category')
        if category:
            details.append(KeyDetail(label="Category", value=category))

        keywords_raw = event.get('keywords', '[]')
        keywords = json.loads(keywords_raw) if isinstance(keywords_raw, str) else keywords_raw
        if keywords:
            location_kw = [k for k in keywords if k.istitle() and len(k) > 3][:2]
            if location_kw:
                details.append(KeyDetail(label="Location", value=", ".join(location_kw)))

    if answer_text:
        lines = answer_text.split('\n')
        in_facts = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Key Facts:") or stripped.startswith("Key Facts"):
                in_facts = True
                stripped = stripped.replace("Key Facts:", "").replace("Key Facts", "").strip(" -*").strip()
                if stripped:
                    details.append(KeyDetail(label="Fact", value=stripped))
                continue
            if stripped.startswith("Sources:"):
                in_facts = False
                continue
            if stripped.startswith("Summary:"):
                continue
            if in_facts and stripped:
                clean = stripped.strip("- *").strip()
                if clean:
                    details.append(KeyDetail(label="Fact", value=clean))
        for prefix in ["Date:", "Location:", "Outcome:", "Casualties:", "Impact:"]:
            for line in lines:
                if line.strip().startswith(prefix):
                    val = line.strip().replace(prefix, "").strip("- *").strip()
                    if val:
                        details.append(KeyDetail(label=prefix.replace(":", ""), value=val))

    seen_labels = set()
    unique = []
    for d in details:
        if d.label not in seen_labels:
            seen_labels.add(d.label)
            unique.append(d)
    return unique[:5]


def _strip_markdown(text):
    if not text:
        return ""
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()


def _clean_llm_output(text):
    if not text:
        return ""
    text = _strip_markdown(text)
    text = re.sub(r'^\*{0,2}(Short Answer|Summary)\*{0,2}\s*[:\-–—]\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\*{0,2}(Short Answer|Summary)\*{0,2}\s*', '', text, flags=re.IGNORECASE)
    text = re.split(r'\n\s*\*{0,2}(Key Details|Key Facts)\*{0,2}\s*[:\-–—]', text, flags=re.IGNORECASE)[0]
    return text.strip()


def _extract_short_answer(answer_text):
    if not answer_text:
        return ""
    text = _clean_llm_output(answer_text)
    sentences = re.split(r'(?<=[.!])\s+', text)
    for s in sentences:
        s = s.strip()
        if len(s) > 15 and len(s) < 400:
            return s
    if sentences:
        first = sentences[0].strip()
        if len(first) > 30 and len(first) < 300:
            return first
    return text[:200].rsplit('.', 1)[0] + '.' if '.' in text[:200] else text[:200]


def _clean_answer(answer_text):
    if not answer_text:
        return ""
    text = _clean_llm_output(answer_text)
    return text


def _extract_topics(event):
    if not event:
        return []
    keywords_raw = event.get('keywords', '[]')
    keywords = json.loads(keywords_raw) if isinstance(keywords_raw, str) else keywords_raw
    topics = [k for k in keywords if k.istitle() and len(k) > 2][:4]
    if event.get('category'):
        topics.insert(0, event['category'])
    return topics


@app.get("/health")
def health():
    return {
        "status": "ok",
        "events_count": db.count_events(),
        "faiss_size": retriever.embeddings.size,
        "llm_configured": bool(llm.api_key),
    }


@app.get("/api/stats")
def stats():
    return {
        "total_events": db.count_events(),
        "by_category": db.count_by_category(),
        "faiss_index_size": retriever.embeddings.size,
    }


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest):
    query_text = req.query.strip()
    if not query_text:
        raise HTTPException(400, "Query cannot be empty")

    year_info = detect_year(query_text)
    if not year_info["is_supported"]:
        unsupported = year_info.get("unsupported_years", [])
        yr = unsupported[0] if unsupported else ""
        return QueryResponse(
            answer=f"This event ({yr}) is outside the supported verification window (2025–2026).",
            short_answer=f"This event ({yr}) is outside the supported verification window (2025–2026).",
            key_details=[KeyDetail(label="Reason", value="Year not supported")],
            confidence="none",
            confidence_score=0,
            verification_status="Not Supported",
            source_type=None,
            evidence="",
            source_references=[],
            why_this_result=[f"Year {yr} falls outside the 2025-2026 coverage window"],
            similarity_score=0,
            title=None,
        )

    context, events = retriever.get_context(query_text)
    top_event = events[0] if events else None

    if context and top_event:
        result = llm.generate(SYSTEM_PROMPT, f"Question: {query_text}\n\nContext:\n{context}")

        sources_raw = top_event.get("sources", "[]")
        sources_list = json.loads(sources_raw) if isinstance(sources_raw, str) else sources_raw

        if result["success"]:
            answer = _clean_answer(result["response"])
        else:
            answer = top_event["summary"]

        confidence_score, verification_status = _compute_confidence(top_event, result, "local")
        key_details = _extract_key_details(answer, top_event)
        short_answer = _extract_short_answer(answer)
        topics = _extract_topics(top_event)

        confidence_label = "high" if confidence_score >= 85 else "medium" if confidence_score >= 60 else "low"
        sim_score = int(top_event.get('_score', 0) * 100) if top_event.get('_score') else None
        sim_display = max(0, min(100, sim_score)) if sim_score else None
        why = [
            f"Source: Knowledge Base ({len(sources_list)} trusted sources)",
        ]
        if sim_display is not None:
            why.append(f"Similarity score: {sim_display}%")
        if confidence_label:
            why.append(f"Confidence tier: {confidence_label.title()}")
        src_refs = [f"[{i+1}] {s}" for i, s in enumerate(sources_list)]

        return QueryResponse(
            answer=answer,
            short_answer=short_answer,
            key_details=key_details,
            confidence=confidence_label,
            confidence_score=confidence_score,
            verification_status=verification_status,
            source_type="local",
            category=top_event.get("category"),
            year=top_event.get("year"),
            sources=sources_list,
            related_topics=topics,
            evidence=answer,
            source_references=src_refs,
            why_this_result=why,
            similarity_score=sim_display,
            title=top_event.get("title"),
        )

    logger.info(f"No local results: '{query_text}'. Trying live search...")
    evidence = live_search.get_evidence(query_text)

    if evidence:
        result = llm.generate(LIVE_SYSTEM_PROMPT, f"Question: {query_text}\n\n{evidence}")
        if result["success"]:
            answer = _clean_answer(result["response"])
            confidence_score, verification_status = _compute_confidence(None, result, "live")
            key_details = _extract_key_details(answer, None)
            short_answer = _extract_short_answer(answer)
            return QueryResponse(
                answer=answer,
                short_answer=short_answer,
                key_details=key_details,
                confidence="medium",
                confidence_score=confidence_score,
                verification_status=verification_status,
                source_type="live",
                related_topics=[],
                evidence=answer,
                source_references=[],
                why_this_result=["Source: Live Search (DuckDuckGo)", "Results analyzed via OpenRouter LLM", "Confidence tier: Medium"],
                similarity_score=None,
                title=None,
            )

    return QueryResponse(
        answer="I couldn't find verified information about this event. Please try a different query.",
        short_answer="I couldn't find verified information about this event.",
        key_details=[KeyDetail(label="Suggestion", value="Try rephrasing or asking about 2025–2026 events")],
        confidence="low",
        confidence_score=0,
        verification_status="Not Found",
        source_type=None,
        evidence="",
        source_references=[],
        why_this_result=["No matching events found in knowledge base or live search"],
        similarity_score=None,
        title=None,
    )


@app.get("/api/events")
def list_events(category: str = None, year: int = None, limit: int = 50):
    if year and year not in {2025, 2026}:
        return {"error": "Only 2025-2026 supported"}

    if year and category:
        events = db.search_by_year(year, category, limit)
    elif year:
        events = db.search_by_year(year, None, limit)
    elif category:
        e2025 = db.search_by_year(2025, category, limit // 2)
        e2026 = db.search_by_year(2026, category, limit // 2)
        events = e2025 + e2026
    else:
        events = db.get_all_events()

    return {"events": events[:limit], "total": len(events)}


# ── Production static file serving (must be last — after all API routes) ──
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST) and os.path.isfile(os.path.join(FRONTEND_DIST, "index.html")):

    @app.get("/{file_path:path}")
    async def serve_frontend(file_path: str):
        if file_path.startswith("api/") or file_path == "health":
            return {"error": "not found"}
        if file_path.startswith("assets/"):
            asset = os.path.normpath(os.path.join(FRONTEND_DIST, file_path))
            if os.path.isfile(asset):
                return FileResponse(asset)
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        return {"error": "not found"}

    logger.info(f"Serving frontend from {FRONTEND_DIST}")
