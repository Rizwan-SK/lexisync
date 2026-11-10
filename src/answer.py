"""Query decomposition -> merged retrieval -> grounded cited answer -> two-gate abstention."""
import json, os, time, anthropic

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
ABSTAIN_BELOW = float(os.getenv("ABSTAIN_CE", "-10.0"))  # tune on dev questions
DECOMPOSE = os.getenv("DECOMPOSE", "1") == "1"            # set DECOMPOSE=0 for the ablation
SPLIT_MODEL = os.getenv("SPLIT_MODEL", "claude-haiku-5-5")  # small model for the planner step (latency/cost optimisation)
SYS = """You are a legal document analyst. Answer ONLY from the numbered sources.
Keep the answer under 150 words. Every claim must cite [doc, page, clause]. Cite only passages that directly support a claim, prefer the operative article over recitals, and never cite a source you did not use. If sources conflict, say so and state which you rely on and why.
If the sources do not contain the answer, set insufficient=true; then answer in one or two sentences saying what is missing, and give no figures from unrelated sources.
Return JSON only: {"answer": str, "citations":[{"doc":str,"page":int,"clause":str}],
"confidence":"HIGH|MEDIUM|LOW","insufficient":bool,"explanation":str}"""
SPLIT = ("Rewrite the user's question as search queries for a legal-document retrieval system. ONLY correct spelling mistakes and, "
         "where the wording is vague, add the legal term likely used (e.g. 'fine' -> 'administrative fines'). Keep the user's own key terms "
         "(e.g. 'co-managers'); never replace them with synonyms and never add concepts that are not in the question. "
         "If the question asks for two or more independent facts, return one query per fact (max 3, each self-contained); "
         "otherwise return exactly ONE query. Return only a JSON list of strings.")

def _text(r): return "".join(b.text for b in r.content if b.type == "text")

def subqueries(client, q):
    try:
        r = client.messages.create(model=SPLIT_MODEL, max_tokens=1000, system=SPLIT, messages=[{"role": "user", "content": q}])
        t = _text(r); qs = [s for s in json.loads(t[t.find("["):t.rfind("]") + 1]) if isinstance(s, str) and s.strip()]
        return qs[:3] or [q]
    except Exception:
        return [q]

def retrieve(index, client, q, k=8):
    """Returns (hits, queries). Planner rewrites/splits the question; each query is searched and results are merged."""
    qs = subqueries(client, q) if DECOMPOSE else [q]
    if qs == [q]: return index.search(q, k=k), [q]
    plan = [(q, 3)] + [(sq, 4) for sq in qs] if len(qs) > 1 else [(qs[0], 6), (q, 4)]   # always also search the user's own wording
    seen, hits = set(), []
    for sq, kk in plan:
        for c, s in index.search(sq, k=kk):
            if id(c) not in seen: seen.add(id(c)); hits.append((c, s))
    return hits[:12], qs

def ask(index, question, docs, k=8):
    t0, client = time.time(), anthropic.Anthropic()
    hits, qs = retrieve(index, client, question, k)
    best = max((s for _, s in hits), default=-99)
    if best < ABSTAIN_BELOW:  # gate 1: retrieval confidence
        return dict(answer=f"The documents do not contain enough evidence to answer this. Searched: {', '.join(docs)}.",
                    citations=[], confidence="INSUFFICIENT EVIDENCE", insufficient=True, queries=qs,
                    explanation=f"Top rerank score {best:.2f} below threshold.", latency=time.time()-t0, hits=hits)
    ctx = "\n\n".join(f"[{i+1}] doc={c.doc} page={c.page} clause={c.clause}\n{c.text}" for i, (c, _) in enumerate(hits))
    r = client.messages.create(model=MODEL, max_tokens=1500, system=SYS,
        messages=[{"role": "user", "content": f"Sources:\n{ctx}\n\nQuestion: {question}"}])
    txt = _text(r)
    try: out = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
    except Exception: out = dict(answer=txt, citations=[], confidence="LOW", insufficient=False, explanation="unparsed")
    if out.get("insufficient"):  # gate 2: LLM-declared abstention
        out["confidence"], out["citations"] = "INSUFFICIENT EVIDENCE", []   # a refusal carries no citations
        out["answer"] += f" Searched: {', '.join(docs)}."
    out.update(latency=time.time()-t0, hits=hits, queries=qs, tokens=(r.usage.input_tokens, r.usage.output_tokens))
    return out
