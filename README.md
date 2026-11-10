# LexiSyncAI
Evidence-grounded legal analyst: clause-aware ingestion → BM25+dense hybrid → cross-encoder rerank → cited answer → two-gate abstention.

## Run
`make install && export ANTHROPIC_API_KEY=... && make run` · eval: `make eval` (arg: PDF dir) · `make test`

## Architecture (draw this as your one-page diagram)
PDF → PyMuPDF (reading order, header/footer strip, scanned flag) → clause-aware chunks → {BM25, bge-small} → RRF → MiniLM cross-encoder → [Gate 1: CE score < threshold ⇒ abstain] → LLM (JSON, cites doc/page/clause) → [Gate 2: insufficient flag] → UI (badge, side-by-side page image).



## Known gaps (TODO)
OCR, table extraction, bbox citations, verifier loop, Dockerfile.
