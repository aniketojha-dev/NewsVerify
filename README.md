# NewsVerify

**News verification system for 2025–2026 + Latest News events using hybrid retrieval (FAISS + SQLite) with OpenRouter LLM fallback.**

Live Link Here : https://newsverify-i7bo.onrender.com

---

## Concept

NewsVerify is a real-time news verification platform that determines whether a reported event is likely true, partially true, or unsupported by cross-referencing it against a curated knowledge base of 1,000+ events and live web search results.

**Core problem:** News spreads faster than verification. Existing fact-checking tools are either manual (slow) or fully LLM-based (hallucination-prone). NewsVerify bridges this gap with a **retrieval-augmented verification** pipeline: events are grounded in a structured knowledge base before any LLM inference occurs.

**Key capabilities:**
- Semantic + keyword hybrid search over a local event database
- Confidence scoring based on source count, FAISS similarity, and LLM corroboration
- Live search fallback via DuckDuckGo when no local match is found
- Year-bound verification window (only 2025–2026), rejecting out-of-range queries
- Concise, structured answers with explicit source references and confidence tiers

---

## Technology

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18 + Vite | Single-page dashboard, 100vh layout, auto-resizing input |
| **Backend** | Python 3.11 + FastAPI | REST API, request routing, response assembly |
| **Vector Search** | FAISS (IndexFlatIP) | 384-dim semantic search using BGE Small embeddings |
| **Embeddings** | fastembed (ONNX runtime) | On-device BGE Small embeddings, no GPU required |
| **Structured Storage** | SQLite | Events, keywords, categories, source metadata |
| **LLM Gateway** | OpenRouter API | Primary: DeepSeek V3 Free → Fallback: Qwen Free → Fallback: Gemma Free |
| **Live Search** | DuckDuckGo (duckduckgo_search) | Web fallback when local KB has no match |
| **RSS Ingestion** | feedparser, aiohttp | Google News RSS, BBC, The Hindu, Indian Express feeds |
| **Clustering** | scikit-learn (TF-IDF + cosine) | Vectorized event deduplication during ingestion |
| **Deployment** | uvicorn + Vite dev server | Local-first, proxies `/api` to backend |

---

## Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                              │
│  "Tell me about the Air India crash"                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ① YEAR DETECTION                                               │
│  • Regex-based year extraction                                 │
│  • Rejects queries with explicit years outside 2025–2026       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ② HYBRID RETRIEVAL                                             │
│  ┌─────────────────────┐  ┌──────────────────────┐             │
│  │ FAISS Semantic      │  │ SQLite Keyword       │             │
│  │  • Embed query      │  │  • LIKE on title/    │             │
│  │    via BGE Small    │  │    summary/keywords   │             │
│  │  • Top-K = 10       │  │  • Year/category     │             │
│  │  • Threshold ≥ 0.6  │  │    filters           │             │
│  └─────────┬───────────┘  └──────────┬───────────┘             │
│            │                          │                        │
│            └──────────┬───────────────┘                        │
│                       ▼                                        │
│            ┌──────────────────────┐                            │
│            │ Merge + Deduplicate │                            │
│            │ Sort by score       │                            │
│            └──────────┬───────────┘                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │     MATCH FOUND IN KB?        │
         └───────┬───────────────┬───────┘
                 │ YES            │ NO
                 ▼                ▼
┌────────────────────────┐  ┌────────────────────────┐
│ ③a LOCAL VERIFICATION  │  │ ③b LIVE SEARCH         │
│  • Build context from  │  │  • DuckDuckGo query    │
│    matched events      │  │  • Scrape top results  │
│  • Send to OpenRouter  │  │  • Send to OpenRouter  │
│    with KB context     │  │    with live snippets  │
│  • LLM produces        │  │  • LLM produces        │
│    structured answer   │  │    structured answer   │
└──────────┬─────────────┘  └──────────┬──────────────┘
           │                           │
           └──────────┬────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ ④ CONFIDENCE SCORING                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ score = base(FAISS) + source_boost + llm_boost          │   │
│  │                                                        │   │
│  │ ≥88 → Verified       72–87 → Likely Verified           │   │
│  │ 60–71 → Plausible     <60 → Low / Not Found            │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ⑤ RESPONSE                                                    │
│  • Short answer (1–2 sentences)                                │
│  • Key facts (extracted dates, locations, outcomes)            │
│  • Confidence score + verification status                      │
│  • Source references + "Why This Result" explanation           │
│  • Related topics for follow-up                                │
└─────────────────────────────────────────────────────────────────┘
```

### Verification logic

```
Event query
    │
    ▼
[FAISS + SQLite search]
    │
    ├── Score > 0.60? ──► Local KB match
    │                       │
    │                       ├── Build context from matched events
    │                       ├── Query OpenRouter with context
    │                       └── Score = 65 + (sources × 4) + 8 (if LLM OK)
    │
    └── No match ──► Live search fallback
                        │
                        ├── DuckDuckGo query
                        ├── Query OpenRouter with snippets
                        └── Score = 68 + 8 (if LLM OK), capped at 85
```

*Built by Aniket Ojha*
