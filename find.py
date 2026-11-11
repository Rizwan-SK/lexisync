"""python find.py data "72 hours"  -> where does this text occur? (whitespace-insensitive; use it to fill gold phrases)"""
import sys, glob, os
sys.path.insert(0, "src")
from ingest import chunk_doc
norm = lambda t: " ".join(t.lower().split()).replace("- ", "")
q = norm(sys.argv[2])
for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.pdf"))):
    for c in chunk_doc(p, os.path.basename(p))[0]:
        if q in norm(c.text): print(c.doc, "p.", c.page, c.clause, "|", c.text[:100].replace("\n", " "))
