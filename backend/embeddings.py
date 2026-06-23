import numpy as np
import json
import os
import logging
from typing import List, Tuple
from fastembed import TextEmbedding
import faiss
from backend.config import FAISS_INDEX_PATH, FAISS_METADATA_PATH

logger = logging.getLogger(__name__)


class EmbeddingIndex:
    def __init__(self):
        self.model = None
        self.index = None
        self.metadata = []
        self.dim = 384

    def _load_model(self):
        if self.model is None:
            logger.info("Loading embedding model (BGE Small via fastembed)...")
            self.model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", max_length=512, cache_dir=None)

    def encode(self, texts: List[str]) -> np.ndarray:
        self._load_model()
        embeddings = list(self.model.embed(texts))
        arr = np.array(embeddings).astype('float32')
        faiss.normalize_L2(arr)
        return arr

    def build_index(self, event_ids: List[int], texts: List[str]):
        self._load_model()
        embeddings = self.encode(texts)
        dim = embeddings.shape[1]
        self.dim = dim
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
        ids = np.array(event_ids, dtype='int64')
        self.index.add_with_ids(embeddings, ids)
        self.metadata = list(event_ids)
        self._save()
        logger.info(f"Built FAISS index with {len(event_ids)} vectors (dim={dim})")

    def add_to_index(self, event_id: int, text: str):
        if self.index is None:
            self.build_index([event_id], [text])
            return
        embedding = self.encode([text])
        eid = np.array([event_id], dtype='int64')
        self.index.add_with_ids(embedding, eid)
        self.metadata.append(event_id)

    def search(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        query_vec = self.encode([query])
        actual_k = min(k, self.index.ntotal)
        scores, indices = self.index.search(query_vec, actual_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                results.append((int(idx), float(score)))
        return results

    def _save(self):
        if self.index is not None:
            faiss.write_index(self.index, FAISS_INDEX_PATH)
        with open(FAISS_METADATA_PATH, 'w') as f:
            json.dump(self.metadata, f)

    def load(self) -> bool:
        if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(FAISS_METADATA_PATH):
            return False
        self.index = faiss.read_index(FAISS_INDEX_PATH)
        with open(FAISS_METADATA_PATH, 'r') as f:
            self.metadata = json.load(f)
        logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
        return True

    @property
    def size(self):
        if self.index is None:
            return 0
        return self.index.ntotal

    def clear(self):
        self.index = None
        self.metadata = []
        for p in [FAISS_INDEX_PATH, FAISS_METADATA_PATH]:
            if os.path.exists(p):
                os.remove(p)
