"""Grounded generation with page-level citations + two-gate abstention."""
import json, os, time, anthropic

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
ABSTAIN_BELOW = float(os.getenv("ABSTAIN_CE", "-10.0"))  # tune on dev questions
SYS = """You are a legal document analyst. Answer ONLY from the numbered sources.
Keep the answer under 150 words. Every claim must cite [doc, page, clause]. If sources conflict, say so and state which you rely on and why.
If the sources do not contain the answer, set insufficient=true.
Return JSON only: {"answer": str, "citations":[{"doc":str,"page":int,"clause":str}],
"confidence":"HIGH|MEDIUM|LOW","insufficient":bool,"explanation":str}"""

def ask(index, question, docs, k=5):
    t0 = time.time()
    hits = index.search(question, k=k)
    best = hits[0][1] if hits else -99
    if best < ABSTAIN_BELOW:  # gate 1: retrieval confidence
        return dict(answer=f"The documents do not contain enough evidence to answer this. Searched: {', '.join(docs)}.",
                    citations=[], confidence="INSUFFICIENT EVIDENCE", insufficient=True,
                    explanation=f"Top rerank score {best:.2f} below threshold.", latency=time.time()-t0, hits=hits)
    ctx = "\n\n".join(f"[{i+1}] doc={c.doc} page={c.page} clause={c.clause}\n{c.text}" for i, (c, _) in enumerate(hits))
    r = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=1500, system=SYS,
        messages=[{"role": "user", "content": f"Sources:\n{ctx}\n\nQuestion: {question}"}])
    txt = "".join(b.text for b in r.content if b.type == "text")
    try: out = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
    except Exception: out = dict(answer=txt, citations=[], confidence="LOW", insufficient=False, explanation="unparsed")
    if out.get("insufficient"):  # gate 2: LLM-declared abstention
        out["confidence"] = "INSUFFICIENT EVIDENCE"
        out["answer"] += f" Searched: {', '.join(docs)}."
    out.update(latency=time.time()-t0, hits=hits, tokens=(r.usage.input_tokens, r.usage.output_tokens))
    return out
