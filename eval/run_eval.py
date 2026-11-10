"""python eval/run_eval.py data -> recall@k per config + eval/results.csv (answers, citation precision, latency)."""
import csv, glob, json, os, random, sys
sys.path.insert(0, "src")
random.seed(42)
from ingest import chunk_doc
from retrieve import Index, MODES
from answer import ask

pdfs = sorted(glob.glob(os.path.join(sys.argv[1], "*.pdf")))
names = [os.path.basename(p) for p in pdfs]
chunks = [c for p in pdfs for c in chunk_doc(p, os.path.basename(p))[0]]
idx = Index(chunks)
norm = lambda t: " ".join(t.lower().split()).replace("- ", "")
Q = json.load(open("eval/questions.json"))
ans = [x for x in Q if x["type"] != "unanswerable"]
def hops(x):  # each gold entry = a phrase; its pages = every page whose chunk text contains it
    out = []
    for g in x["gold"]:
        pg = {(c.doc, c.page) for c in chunks if c.doc == g["doc"] and norm(g["contains"]) in norm(c.text)}
        if not pg: print(f"WARNING phrase not found, fix it: {g['doc']!r} {g['contains']!r}")
        else: out.append(pg)
    return out
for x in Q: x["hops"] = hops(x)
gold = lambda x: set().union(*x["hops"]) if x["hops"] else set()

for k in (3, 5, 10):  # fraction of gold pages found in top-k
    for m in MODES:
        r = [sum(bool(h & {(c.doc, c.page) for c, _ in idx.search(x["q"], k, m)}) for h in x["hops"]) / len(x["hops"]) for x in ans if x["hops"]]
        print(f"recall@{k:<2} {m:<14} {sum(r)/len(r):.2f}")

rows = []
for x in Q:
    o = ask(idx, x["q"], names)
    cited = {(c["doc"], c["page"]) for c in o["citations"]}
    prec = len(cited & gold(x)) / len(cited) if cited else None
    rows.append(dict(type=x["type"], question=x["q"], abstained=o["insufficient"], confidence=o["confidence"],
                     citation_precision=prec, latency_s=round(o["latency"], 1), tokens=o.get("tokens"),
                     answer=o["answer"], explanation=o.get("explanation", ""),
                     cited="; ".join(f"{d} p.{p}" for d, p in sorted(cited)),
                     retrieved="; ".join(f"p.{c.page} {c.clause}" for c, _ in o["hits"]), queries=" | ".join(o.get("queries", [])), correct_manual=""))
un = [r for r in rows if r["type"] == "unanswerable"]; an = [r for r in rows if r["type"] != "unanswerable"]
print(f"abstention accuracy: {sum(r['abstained'] for r in un)}/{len(un)}   false abstentions: {sum(r['abstained'] for r in an)}/{len(an)}")
ps = [r["citation_precision"] for r in an if r["citation_precision"] is not None]
print(f"mean citation precision: {sum(ps)/max(len(ps),1):.2f}   mean latency: {sum(r['latency_s'] for r in rows)/len(rows):.1f}s")
with open("eval/results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
