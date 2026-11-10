"""python eval/run_eval.py data -> recall@k per config + eval/results.csv (answers, citation precision, latency)."""
import csv, glob, json, os, random, sys
sys.path.insert(0, "src")
random.seed(42)
from ingest import chunk_doc
from retrieve import Index, MODES
from answer import ask

pdfs = sorted(glob.glob(os.path.join(sys.argv[1], "*.pdf")))
names = [os.path.basename(p) for p in pdfs]
idx = Index([c for p in pdfs for c in chunk_doc(p, os.path.basename(p))[0]])
Q = json.load(open("eval/questions.json"))
ans = [x for x in Q if x["type"] != "unanswerable"]
gold = lambda x: {(g["doc"], g["page"]) for g in x["gold"]}

for k in (3, 5, 10):  # fraction of gold pages found in top-k
    for m in MODES:
        r = [len(gold(x) & {(c.doc, c.page) for c, _ in idx.search(x["q"], k, m)}) / len(gold(x)) for x in ans]
        print(f"recall@{k:<2} {m:<14} {sum(r)/len(r):.2f}")

rows = []
for x in Q:
    o = ask(idx, x["q"], names)
    cited = {(c["doc"], c["page"]) for c in o["citations"]}
    prec = len(cited & gold(x)) / len(cited) if cited else None
    rows.append(dict(type=x["type"], question=x["q"], abstained=o["insufficient"], confidence=o["confidence"],
                     citation_precision=prec, latency_s=round(o["latency"], 1), tokens=o.get("tokens"),
                     answer=o["answer"], correct_manual=""))
un = [r for r in rows if r["type"] == "unanswerable"]; an = [r for r in rows if r["type"] != "unanswerable"]
print(f"abstention accuracy: {sum(r['abstained'] for r in un)}/{len(un)}   false abstentions: {sum(r['abstained'] for r in an)}/{len(an)}")
ps = [r["citation_precision"] for r in an if r["citation_precision"] is not None]
print(f"mean citation precision: {sum(ps)/max(len(ps),1):.2f}   mean latency: {sum(r['latency_s'] for r in rows)/len(rows):.1f}s")
with open("eval/results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
