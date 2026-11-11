# LexiSyncAI – evidence-grounded legal document analyst

Upload 2–5 public legal PDFs, ask a question, and get a plain-language answer where **every claim cites a page and clause**.
The app shows the cited passage next to the rendered PDF page, a confidence badge, and **refuses to answer** when the documents
do not contain the evidence (listing which documents it searched).

## Quick start (Windows PowerShell)

**You need:** Git, Anaconda or Miniconda, and an Anthropic API key with credit ([console.anthropic.com](https://console.anthropic.com)).

**1. Get the code**

```
git clone https://github.com/Rizwan-SK/lexisync.git
cd lexisync
```

**2. Create the environment** (Python 3.12; the pinned versions in `requirements.txt` were frozen from a working install)

```
conda create -n lexisync python=3.12 -y
conda activate lexisync
pip install -r requirements.txt
```

**3. Set your API key** (once per terminal window; never commit it)

```
$env:ANTHROPIC\_API\_KEY = "your-key-here"
```

**4. Start the app**

```
python -m streamlit run src/app.py --server.fileWatcherType none
```

Open the address it prints (usually http://localhost:8501). The first start downloads the embedding and reranker models, which takes a few minutes.

**5. Use it:** upload PDFs in the sidebar → click **Index** (the sidebar then shows pages, chunks and any scanned pages) → ask a question.
Try these three on `gdpr.pdf`:

* *Multi-hop:* "Under the GDPR, what is the maximum fine, and which violations trigger the higher fine?" → cites Art. 83(4) and 83(5), pages 82–83.
* *Prose:* "Within what time must a controller notify a personal data breach?" → 72 hours, Art. 33(1).
* *Unanswerable:* "What is the governing law of the subcontractor agreement?" → red INSUFFICIENT EVIDENCE badge, no citations.

Mac/Linux: identical, except `export ANTHROPIC\_API\_KEY="your-key-here"` in step 3.

**Run the tests:** `python -m pytest -q`  ·  **Run the evaluation:** put `gdpr.pdf` and `google.pdf` in a folder `data\_core/`, then `python eval/run\_eval.py data\_core` (calls the API; prints the recall table, writes `eval/results.csv`).
`make install | run | eval | test` are shortcuts for the same commands (`make` is optional).

**Settings (optional environment variables)**

|Variable|Default|Meaning|
|-|-|-|
|`LLM\_MODEL`|`claude-sonnet-5-5`|model that writes the cited answer|
|`SPLIT\_MODEL`|`claude-haiku-5-5`|smaller model for the query planner|
|`DECOMPOSE`|`1`|`0` switches the planner off (used for the ablation)|
|`ABSTAIN\_CE`|`-10`|rerank-score threshold for the first abstention gate|

**Troubleshooting:** "Application Control policy blocked streamlit.exe" → always start with `python -m streamlit` as above ·
`ModuleNotFoundError` → run `conda activate lexisync` and reinstall requirements · everything abstains or errors → check the API key and credit.

## How it works

!\[LexiSyncAI architecture](docs/architecture.svg)

* **Ingestion** (`src/ingest.py`): reads each page in column-aware order, strips headers/footers, flags image-only pages, and splits text at clause boundaries
(`Article 83 (4)`, `Recital 86`, contract clauses like `7.2`, ALL-CAPS headings, else `p.N`), never mid-clause unless a clause exceeds 1,200 characters. Every chunk keeps its own document, page and clause.
* **Retrieval** (`src/retrieve.py`): BM25 (good for clause numbers) + dense embeddings, merged by reciprocal rank fusion, reranked by a cross-encoder.
* **Planner** (`src/answer.py`): a small model fixes spelling, uses legal terminology, and splits multi-part questions into sub-queries; the user's own wording is searched too.
* **Answer and abstention**: the LLM may use only the retrieved passages and returns JSON with citations and a confidence level. Abstention has two gates: a low rerank score, or the model declaring the evidence insufficient. A refusal carries no citations.

**Requirement coverage**

|Assignment requirement|Where|
|-|-|
|Ingestion, reading order, scanned-page flag, clause-aware chunking|`src/ingest.py`, `tests/`|
|Hybrid retrieval + cross-encoder rerank, recall@k per configuration|`src/retrieve.py`, `eval/run\_eval.py`|
|Cited generative answer, answers only from context, cited page shown|`src/answer.py`, `src/app.py`|
|Abstention, accuracy on unanswerable questions|two gates; 4/4 below|
|≥15 questions (factual, multi-hop, ≥3 unanswerable), correctness, citation precision, latency, mandatory comparison|17 questions; dense-only vs hybrid vs hybrid+rerank (below)|
|Extended features|query planner with ablation, latency/token report, measured model optimisation (below)|

## Data (not committed)

`data\_core/` holds the two evaluation documents: `gdpr.pdf` (Regulation (EU) 2016/679, https://eur-lex.europa.eu/eli/reg/2016/679/oj)
and `google.pdf` (Alphabet Inc. notes pricing term sheet, SEC EDGARhttps://www.sec.gov/Archives/edgar/data/1652044/000119312526443857/d134038dfwp.htm). PDFs are git-ignored.

## Evaluation

17 questions in `eval/questions.json`: 8 factual, 5 multi-hop (two clauses or pages), 4 unanswerable. Gold answers are phrases that must appear on the cited page;
recall = share of gold "hops" whose page is in the top-k.

**Retrieval recall@k (13 answerable questions)**

|Config|k=3|k=5|k=10|
|-|-|-|-|
|BM25|0.65|0.77|0.88|
|Dense|0.92|0.92|0.92|
|Hybrid (RRF)|0.77|0.92|0.92|
|Hybrid + cross-encoder|0.85|0.85|0.92|

Dense is strongest at k=3; plain hybrid matches it from k=5; everything but BM25 converges at k=10. BM25 alone is weakest because the questions are natural language, not clause numbers.
The general-purpose cross-encoder lifts hybrid at k=3 but trails plain hybrid at k=5, which fits a reranker trained on web search rather than legal text.
A 0.04 gap is half of one gold hop, so small differences are noise.

**End-to-end results by system version**

|Version|What changed|Abstention acc.|False abstentions|Citation precision|Mean latency|
|-|-|-|-|-|-|
|No planner|single query, top 5 chunks|4/4|3/13|0.81|4.4 s|
|v1|Sonnet splits multi-part questions|4/4|0/13|0.79|6.6 s|
|v2|Haiku splitter; stricter split and citation prompts|4/4|1/13|0.88|5.6 s|
|v3|LLM query rewrite; 8 chunks|4/4|1/13|0.91|6.1 s|
|v4|rewrite limited to spelling and legal terms; user's wording also searched; concise refusals|4/4|1/13|0.90|5.7 s|
|v5|robust JSON parsing, one retry on truncated replies|4/4|1/13|0.92|6.2 s|
|**v6 (final)**|ingestion fix: footer filter no longer drops text in the bottom 6% of a page|4/4|1/13|0.90|5.4 s|

* The planner removed the multi-hop refusals: without it, all 3 false abstentions were two-part questions matched as one query. It costs about 1–2 s per question.
* Moving the splitter from Sonnet to Haiku cut latency by 1.0 s (v1 → v2, which also changed two prompts).
* v4 → v5 reflects a bug fix, not retrieval: 2 of 17 v4 answers were shown as raw model output and counted without citations.
* v6 made the consent-age answer complete (Art. 8(1) allows Member States to lower the age to 13). Precision moved 0.92 → 0.90 because one answer now also cites a correct page that is not in the gold set.
* v3/v4 target misspelled or vague questions, which the clean question set does not measure; they were verified on such queries in the app.

**Answer correctness (manual, by the author, v6, `eval/results\_decompose\_v6.csv`): 16 correct, 1 partial, 0 incorrect of 17.**
The partial is the DPIA + fine question (the model answered the DPIA half and reported that the retrieved sources held no Art. 83(4) text). All 4 unanswerable questions were refused with no citations.
Citation precision is strict page-level against the gold phrase, so a relevant extra page counts as an error. Each version was run once; n=17, so one question is about 6 points.
Raw per-question results for every version are in `eval/results\_\*.csv`.

## Findings and limitations

* **Remaining miss:** the fine for ignoring a DPIA. Art. 83(4) says "Articles 25 to 39" and never names Art. 35, so retrieval misses it; the system refused instead of guessing.
* **Bugs found through error analysis and fixed:** the page-margin filter dropped text near the bottom of a page (Art. 8(1)'s exception for age 13; regression test added); model replies with trailing text were not parsed; an unconstrained query rewrite replaced "co-managers" with a synonym and missed the passage.
* **Near-duplicate documents:** when two copies of the same regulation were indexed, duplicate chunks filled the retrieval slots and pushed Art. 83(4)/(5) out. Retrieving a few chunks per document would address this.
* **Known limitations:** recital chunks can carry the wrong recital number; the confidence badge is model-reported and varies between runs; scanned pages are flagged but not OCR'd; tables get no special extraction; LLM output is not seeded.

## Layout

`src/ingest.py` · `src/retrieve.py` · `src/answer.py` (planner, generation, abstention) · `src/app.py` (Streamlit UI) · `eval/` (questions, harness, results) · `find.py` (locate text and pages in PDFs) · `tests/` · `requirements.txt` · `Makefile`

