"""BM25 + dense -> RRF fusion -> cross-encoder rerank."""
import re, numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

tok = lambda s: [t.strip(".") for t in re.findall(r"[\w.]+", s.lower()) if t.strip(".")]
MODES = ["bm25", "dense", "hybrid", "hybrid+rerank"]

class Index:
    def __init__(self, chunks, emb="BAAI/bge-small-en-v1.5", ce="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.c = chunks
        self.bm = BM25Okapi([tok(c.clause + " " + c.text) for c in chunks])
        self.emb, self.ce = SentenceTransformer(emb), CrossEncoder(ce)
        self.V = self.emb.encode([c.text for c in chunks], normalize_embeddings=True)

    def _rank(self, q, mode, n=30):
        if mode == "bm25": return list(np.argsort(-self.bm.get_scores(tok(q)))[:n])
        qv = self.emb.encode([q], normalize_embeddings=True)[0]
        return list(np.argsort(-(self.V @ qv))[:n])

    def search(self, q, k=5, mode="hybrid+rerank"):
        """Returns [(chunk, score)]; score is the CE logit in rerank mode (used for abstention)."""
        if mode in ("bm25", "dense"):
            return [(self.c[i], 0.0) for i in self._rank(q, mode)[:k]]
        rrf = {}
        for m in ("bm25", "dense"):
            for r, i in enumerate(self._rank(q, m)): rrf[i] = rrf.get(i, 0) + 1/(60+r)
        top = sorted(rrf, key=rrf.get, reverse=True)[:20]
        if mode == "hybrid": return [(self.c[i], rrf[i]) for i in top[:k]]
        s = self.ce.predict([(q, self.c[i].text) for i in top])
        return [(self.c[top[j]], float(s[j])) for j in np.argsort(-s)[:k]]
