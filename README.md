# InsureTutor

A conversational tutor for the **FLEXI-ULife Prime Saver** brochure. Ask in English, Simplified Chinese or Traditional Chinese, inspect the cited text and open its PDF page.

Vue 3 + TypeScript · FastAPI + Python · persistent Chroma. API keys stay on the backend.

## Run with Docker

Requires Docker with Compose and an OpenAI API key with access to the configured models.

```bash
git clone https://github.com/newDarwin100/InsureTutor.git
cd InsureTutor
cp .env.example .env
# Edit .env: set OPENAI_API_KEY and models available to your account.
bash scripts/start.sh
```

Open **http://127.0.0.1:8000** after readiness is reported.

On first start, the container validates the checked-in data and embeds **143 text chunks** into a named volume. This sends brochure text to OpenAI and incurs embedding usage. Subsequent starts reuse an unchanged index. Changes to sources, model or dimensions produce a new index version; completed batches can resume, and activation happens only after the build completes.

After image construction, the script waits up to 10 minutes for local RAG readiness. Dependency downloads during the image build may take longer. A failure prints recent logs and requires an explicit retry.

```bash
docker compose logs -f app     # Index and server progress
docker compose down           # Stop; retain the index
bash scripts/start.sh         # Restart or retry after fixing configuration
```

Do not use `docker compose down -v` unless you intend to delete the index and pay to rebuild it. The local development index and Docker volume are separate.

**Validation status:** initialization and reuse are covered by offline tests. Docker is not installed on the development machine; an actual image build and fresh-volume run remain unverified.

## Try the demo

- “Is the 4% interest rate guaranteed?”
- “被裁员后能停缴多久？附加保障也适用吗？”
- “定期提款有什么条件？” — then “那每年提款呢？”

Language selection changes the interface and subsequent answers. Earlier messages and quotations retain their original language. Click a citation number to reveal its text and PDF link. Page numbers count the cover; direct PDF jumping depends on browser support.

Each page gets a separate session. “Clear conversation” deletes backend history. Sessions expire after 30 idle minutes and disappear on restart; credentials stay in page memory.

The Performance tab shows per-request latency, its cumulative average, a latency histogram and average/median/minimum/maximum values. Switch between returned requests on this page and separate saved test sets; timing stages can be filtered. Request details and token usage are collapsed by default. Page measurements stay in browser memory (latest 200, reset on refresh); opening the tab does not call a model or persist conversations.

## Architecture

```mermaid
flowchart TD
    User --> UI[Vue chat · three languages]
    UI --> API[FastAPI]
    API --> Guard[Input guardrail]
    Guard --> Context[Resolve follow-up if needed]
    Context --> Embed[Embed the question]
    Embed --> DB[(Chroma · Top-K 5)]
    DB --> Evidence[Evidence + linked conditions and footnotes]
    Evidence --> Draft[LLM answer with evidence IDs]
    Draft --> Check[Citation validation + model evidence check]
    Check --> Result[Answer · sources · timings]
    Result --> UI
    Result --> PDF[Original PDF page]
```

Clear misuse requests stop before retrieval; ambiguous follow-ups ask for clarification. Unsupported drafts are withheld. Optional repair allows at most one additional attempt.

History resolves what a follow-up refers to. Every answer retrieves fresh PDF evidence; previous assistant text is not a factual source.

## Design decisions

| Decision | Choice and reason | Trade-off |
| --- | --- | --- |
| Frontend | Vue + Vite, one chat page and plain CSS cover the required interactions. | No larger application framework or component library. |
| Orchestration | Small Python modules with explicit provider calls make context and usage inspectable. | Validation and error handling are implemented locally. |
| Database | Embedded Chroma persists one small brochure without a separate service. | Larger corpora and concurrent workloads need a measured storage/service comparison. |
| Parsing | MinerU JSON preserves text, layout and tables; targeted PDF checks resolve gaps. | Some image-only content is unindexed. PyMuPDF/pypdf support inspection; they do not replace reviewed extraction. |
| Chunking | Sections, table rows and footnote links; 1,200-character cap, 120-character overlap for long passages. | More bookkeeping than fixed windows. Character limits are not token limits. |
| Languages | Align original English and Traditional Chinese; generate Simplified Chinese answers from those sources. | Translations are never labeled as original PDF quotations. |
| Citations | The model selects IDs; the server supplies text, filename and page. Display groups sources by page. | Valid IDs alone do not prove semantic support. |
| Guardrails | Input rules, model scope classification and output evidence checks; conflicts apply to disputed fields. | Rules and model checks can miss errors or reject valid answers. |
| Memory | Backend memory: 8 turns, 24,000 characters, 30-minute idle expiry, one worker. | Restart clears history; multiple instances need shared storage and access control. |
| Models | Configurable LLM; saved reports use `gpt-5.6-luna` and `text-embedding-3-large`. | Check account availability. No controlled model comparison is complete. |
| Deployment | Multi-stage Docker build; FastAPI serves the compiled frontend. | First startup needs embedding access; local readiness cannot prove remote model availability. |

### A retrieval failure that shaped the design

An English unemployment question retrieved the **365-day special grace period** but missed the next page's **Basic Plan only** footnote. Following the reviewed body-to-footnote link recovered the missing restriction.

We keep smaller retrieval chunks and expand known relationships before increasing Top-K or adding a reranker. Direct recall and expanded coverage are scored separately. Expansion cannot help when the relevant body text was never retrieved.

[Execution notes](docs/EXECUTION.md) · [full retrieval report](evaluation/results/full-large.md).

## Configuration and cost

Copy `.env.example` to `.env`; never commit the real key.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Backend-only credential. |
| `LLM_MODEL` | Generation, evidence check and optional follow-up resolution. |
| `EMBEDDING_MODEL` | Document/query embeddings; default `text-embedding-3-large`. |
| `EMBEDDING_DIMENSIONS` | Optional override; changing it requires a new index. |
| `RAG_TOP_K` | Initial retrieval count; default 5. |
| `ANSWER_REPAIR_ENABLED` | Default `false`; `true` permits one extra generation/check attempt. |

Ordinary questions use a query embedding, generation and evidence check. Contextual follow-ups may add a resolution call; enabled repair adds usage. Responses show actual timings and provider usage. Unknown report values remain blank.

This brochure includes historical illustrations; answers explain its stated terms rather than claim its rates or fees are current.

## Local development

Requires **Python 3.12** and **Node.js 22.12+** (or 20.19+). From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
cp .env.example .env
# Edit .env before the next command.
.venv/bin/python scripts/build_index.py --full
bash scripts/dev.sh
```

Keep an existing `.env`. Indexing calls the embedding API only for missing chunks; the development launcher does not build indexes or install dependencies.

Frontend: **http://127.0.0.1:5173**. API docs: **http://127.0.0.1:8000/docs**. Ctrl+C stops both services. Stop Docker before development; both use port 8000.

## Checks and evaluation

Offline tests use deterministic or mocked providers, without paid calls:

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
.venv/bin/python scripts/check_full_alignment.py
.venv/bin/python scripts/evaluate_retrieval.py
npm test --prefix frontend
npm run build --prefix frontend
```

With a server running, `.venv/bin/python scripts/check_local.py` checks the built page, assets, health, PDF byte ranges and private-path isolation without calling a model.

| Endpoint | Meaning |
| --- | --- |
| `/health/live` | The API process responds. |
| `/health/ready` | Key configuration, reviewed sources and current index are locally ready; otherwise 503. Docker uses this endpoint. |

Readiness does **not** check API balance, model access or answer quality.

### Saved measurements

| Test set | Direct mean Recall@5 | Coverage after linked evidence expansion |
| --- | ---: | ---: |
| 12-chunk pilot, 12 multilingual questions | 95.83% | 100% |
| 143-chunk full index, 12 multilingual questions | 87.50% | 100% |
| Full index, 8 reference retrieval questions | 93.75% | 100% |

These small development sets measure retrieval, not overall answer correctness. [Reports](evaluation/results/full-large.json) preserve rankings and usage; cached timings remain the original measurements.

The dashboard includes **38 historical rows**, including failures and two unexecuted safety cases. One answer passed the model check but human review found missing withdrawal conditions. This prompted context expansion; that run is not an independently verified correct answer. See [answer checks](evaluation/results/single-turn.md).

Paid evaluations are separate, explicit commands:

```bash
.venv/bin/python scripts/run_retrieval_pilot.py
.venv/bin/python scripts/run_full_retrieval.py
.venv/bin/python scripts/check_answers.py --run
```

They send fixed questions and/or brochure text to OpenAI and may incur usage. Retrieval scripts reuse index/query caches; check cache fields before treating a run as a fresh latency measurement.

## Source data and remaining work

Checked-in data contains **292 evidence records and 143 chunks**, source hashes, physical pages, table structure and reviewed bilingual relationships. Raw MinerU exports and local indexes are excluded from Git and the image. Fresh Docker startup uses reviewed processed data.

Two genuine bilingual discrepancies remain: an age boundary and minimum amounts for a sum-insured change. They are not silently reconciled. See the [source review](data/reviewed/full_alignment.md).

Remaining submission gates: an actual Docker build/fresh-volume run and complete answer-level checks across languages, multi-turn cases and safety false positives. Some chart content is not indexed. Model verification can misjudge support. No load test or controlled model comparison has been reported.

## Repository guide

| Path | Contents |
| --- | --- |
| `frontend/src/` | Chat, translations, citations and evaluation panel. |
| `backend/app/` | API, retrieval, guardrails, model calls and sessions. |
| `backend/tests/` | Offline regression tests. |
| `data/processed/`, `data/reviewed/` | Knowledge and source review. |
| `evaluation/` | Reference questions, scoring and saved reports. |
| `scripts/` | Preparation, indexing, checks and launchers. |
| `docs/` | Supplied PDF, task and Chinese [execution log](docs/EXECUTION.md). |
