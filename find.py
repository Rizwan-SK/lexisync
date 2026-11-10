"""python find.py data "72 hours"  -> where does this text occur? Use it to fill gold pages."""
import sys, glob, os
sys.path.insert(0, "src")
from ingest import chunk_doc
q = sys.argv[2].lower()
for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.pdf"))):
    for c in chunk_doc(p, os.path.basename(p))[0]:
        if q in c.text.lower(): print(c.doc, "p.", c.page, c.clause, "|", c.text[:100].replace("\n", " "))
