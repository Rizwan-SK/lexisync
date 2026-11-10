import os, sys, tempfile, fitz, streamlit as st
sys.path.insert(0, os.path.dirname(__file__))
from ingest import chunk_doc
from retrieve import Index
from answer import ask

st.set_page_config(page_title="LexiSyncAI", layout="wide")
st.title("LexiSyncAI – evidence-grounded legal analyst")
ss = st.session_state
with st.sidebar:
    st.header("Case")
    files = st.file_uploader("Upload 2–5 PDFs", type="pdf", accept_multiple_files=True)
    if st.button("Index") and files:
        d, chunks, ss.paths, ss.struct = tempfile.mkdtemp(), [], {}, {}
        for f in files:
            p = os.path.join(d, f.name); open(p, "wb").write(f.read())
            c, s = chunk_doc(p, f.name); chunks += c; ss.paths[f.name], ss.struct[f.name] = p, s
        with st.spinner("Embedding…"): ss.index = Index(chunks)
    for n, s in ss.get("struct", {}).items():
        st.write(f"**{n}**: {s['pages']} pages, {s['chunks']} chunks" + (f", ⚠ scanned: {s['scanned_pages']}" if s["scanned_pages"] else ""))

if "index" in ss:
    q = st.text_input("Ask a question about the documents")
    if q:
        r = ask(ss.index, q, list(ss.paths))
        badge = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🟠"}.get(r["confidence"], "🔴")
        st.subheader(f"{badge} {r['confidence']}"); st.write(r["answer"])
        if r.get("explanation"): st.caption(r["explanation"])
        st.caption(f"{r['latency']:.1f}s · tokens {r.get('tokens', '-')}")
        if r.get("queries") and r["queries"] != [q]: st.caption("Searched for: " + "  |  ".join(r["queries"]))
        with st.expander(f"Retrieved passages ({len(r['hits'])})"):
            for c, sc in r["hits"]: st.write(f"{c.doc} · p.{c.page} · {c.clause} · score {sc:.2f}")
        for c in r["citations"]:
            with st.expander(f"{c['doc']} · p.{c['page']} · {c['clause']}"):
                left, right = st.columns(2)
                src = next((x for x, _ in r["hits"] if x.doc == c["doc"] and x.page == c["page"]), None)
                left.text(src.text if src else "(chunk not in retrieved set)")
                if c["doc"] in ss.paths:
                    with fitz.open(ss.paths[c["doc"]]) as d:
                        right.image(d[c["page"]-1].get_pixmap(dpi=90).tobytes("png"))
