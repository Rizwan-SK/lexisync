# LexiSyncAI
Evidence-grounded legal analyst: clause-aware ingestion → BM25+dense hybrid → cross-encoder rerank → cited answer → two-gate abstention.

## Run
`make install && export ANTHROPIC_API_KEY=... && make run` · eval: `make eval` (arg: PDF dir) · `make test`

## Architecture (draw this as your one-page diagram)
PDF → PyMuPDF (reading order, header/footer strip, scanned flag) → clause-aware chunks → {BM25, bge-small} → RRF → MiniLM cross-encoder → [Gate 1: CE score < threshold ⇒ abstain] → LLM (JSON, cites doc/page/clause) → [Gate 2: insufficient flag] → UI (badge, side-by-side page image).

## 3-day plan
**Day 1 (Mon 9):** install, get 2–3 PDFs (GDPR from EUR-Lex + a SEC/gov.uk doc), run ingestion, inspect chunks. Commit often.
**Day 2 (Tue 10):** write ≥15 questions in eval/questions.json (≥3 unanswerable, ≥3 two-page multi-hop; fill real gold pages). Run `make eval`, tune ABSTAIN_CE. Do the mandatory comparison (dense vs hybrid, or no-retrieval vs retrieval).
**Day 3 (Wed 11):** UI polish, README/diagram, rehearse 5-min demo on an *unseen* PDF. Bonus if time: #11 latency/cost (already logged), #5 verifier loop, #10 Streamlit Cloud deploy.

## Known gaps (TODO)
OCR, table extraction, bbox citations, verifier loop, Dockerfile.
