"""Print top rerank scores for answerable vs unanswerable questions -> pick ABSTAIN_CE between them."""
import sys, glob, os
sys.path.insert(0, "src")
from ingest import chunk_doc
from retrieve import Index

pdfs = glob.glob("data/*.pdf")
idx = Index([c for p in pdfs for c in chunk_doc(p, os.path.basename(p))[0]])
QS = [
 ("ANSWER", "Under the GDPR, what is the maximum fine, and which violations trigger the higher fine?"),
 ("ANSWER", "Within what time must a personal data breach be notified to the supervisory authority?"),
 ("ANSWER", "When must a controller designate a data protection officer?"),
 ("NOANS",  "What is the governing law of the subcontractor agreement?"),
 ("NOANS",  "What is the penalty for tax evasion under US federal law?"),
 ("NOANS",  "What is the liability cap in the vendor contract?"),
]
for kind, q in QS:
    hits = idx.search(q, k=3)
    print(f"\n[{kind}] {q}")
    for c, s in hits:
        print(f"   {s:6.2f}  {c.doc} p.{c.page}  {c.clause}")
