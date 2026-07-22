# Industrial Knowledge Intelligence — Hackathon Winning Extension

Extended build for ET AI Hackathon, PS8: **AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain**.

This version upgrades the original Expert Knowledge Copilot core into a much stronger demo scope with:
- multi-format ingestion
- OCR for scanned records
- industrial entity extraction
- metadata-rich retrieval
- knowledge graph intelligence
- supervisor-routed copilot
- RCA agent
- compliance checker
- lessons learned engine
- proactive alerts
- dashboard, document explorer, and graph view
- evaluation harness and demo-corpus generator

## Implemented modules

| Module | Status | Notes |
|---|---|---|
| PDF ingestion | ✅ | Existing core preserved |
| DOCX ingestion | ✅ | `python-docx` based |
| Excel / CSV ingestion | ✅ | `pandas` + `openpyxl` |
| OCR / scanned documents | ✅ | `pytesseract` + `pdf2image` + Pillow |
| Entity extraction | ✅ | Groq structured extraction + verification pass |
| Metadata management | ✅ | per-chunk source/page/category/file type |
| Knowledge graph | ✅ | NetworkX graph; Neo4j-ready conceptual model |
| Advanced RAG | ✅ | multi-query + cross-encoder reranking |
| RCA agent | ✅ | graph history + RAG evidence |
| Compliance checker | ✅ | gap detection + auto-drafted correction |
| Lessons learned engine | ✅ | recurring failure mining + recommendations |
| Agentic supervisor | ✅ | lightweight router instead of full LangGraph |
| Alerts | ✅ | in-dashboard proactive warnings |
| Frontend dashboard | ✅ | Flask + HTML/JS demo UI |
| Document explorer | ✅ | inventory by file, type, category |
| Knowledge graph visualization | ✅ | lightweight SVG visualization + optional PyVis export |
| Evaluation metrics | ✅ | benchmark script + example dataset |
| Demo corpus generator | ✅ | synthetic multi-format seed set |
| P&ID vision parsing | ⏳ Roadmap | high-innovation optional future scope |
| PostgreSQL/Auth | ⏳ Roadmap | can be added after demo freeze |

## Project structure

```text
industrial-knowledge-copilot/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
├── data/
│   └── eval_questions.example.json
├── src/
│   ├── ingest.py
│   ├── extract_entities.py
│   ├── knowledge_graph.py
│   ├── query.py
│   ├── rca_agent.py
│   ├── compliance_agent.py
│   ├── supervisor_agent.py
│   ├── evaluate.py
│   └── create_demo_corpus.py
└── outputs_store/
```

## Why this scope is stronger for judging

This project now demonstrates the exact journey judges like to see:
1. **Documents come in from multiple real-world industrial formats**
2. **The system extracts industrial entities and relationships**
3. **The graph connects equipment, failures, causes, and regulations**
4. **The copilot answers with citations**
5. **RCA goes beyond Q&A into operational decision support**
6. **Compliance analysis shows measurable business value**
7. **Lessons learned and alerts make it proactive, not just reactive**
8. **The dashboard makes the project demo-ready**

## Setup

### 1) Python environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2) OCR system packages

```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils

# macOS
brew install tesseract poppler
```

### 3) Environment variables

Copy `.env.example` to `.env` and add your Groq API key.

## Fastest hackathon demo path

If you do **not** already have plant documents, generate a demo corpus:

```bash
python src/create_demo_corpus.py
```

That creates:
- maintenance history CSV with recurring failures
- plant SOP DOCX
- OISD guideline DOCX
- equipment manual DOCX
- scanned inspection image for OCR

## Build pipeline

Run the full pipeline in order:

```bash
python src/ingest.py
python src/extract_entities.py
python src/knowledge_graph.py
python app.py
```

Open:

```text
http://localhost:5000
```

## Dashboard capabilities

### Copilot
Supervisor-routed industrial Q&A with cited sources and advanced retrieval.

### RCA Agent
Enter an equipment tag such as `Pump P101` and generate a structured RCA report grounded in graph history and manuals/logs.

### Compliance Checker
Paste a plant procedure and compare it to retrieved regulatory guidance. The system identifies the gap and drafts a corrected section.

### Alerts
Shows recurring failure patterns as proactive warning cards.

### Document Explorer
Lists ingested files, types, categories, pages, and chunk counts.

### Knowledge Graph
Visualizes the relationship network across equipment, failures, causes, documents, and regulations.

### Lessons Learned
Summarizes repeated incidents and prevention recommendations.

## Evaluation metrics

Use the benchmark harness:

```bash
python src/evaluate.py
```

To customize, add:

```text
data/eval_questions.json
```

Expected format:

```json
[
  {
    "question": "What does the OISD guideline require for emergency shutdown testing?",
    "expected_keywords": ["6 months", "emergency shutdown"],
    "expected_sources": ["oisd_hot_work_guideline.docx"]
  }
]
```

Tracked metrics:
- average latency
- source precision@K
- keyword recall in answer

## Suggested demo story for judges

1. Start with **Document Explorer** to show mixed-format ingestion.
2. Ask the **Copilot** a regulation question and show citations.
3. Run **RCA** on `Pump P101` to show incident intelligence.
4. Open **Compliance** and use the demo SOP gap.
5. Open **Alerts** and **Lessons Learned** to show proactive value.
6. End with the **Knowledge Graph** as the system’s unified brain.

## Honest roadmap / future scope

To keep the demo stable and hackathon-friendly, a few enterprise-scale features are intentionally left as next-step upgrades:
- Neo4j instead of in-process NetworkX
- LangGraph multi-agent orchestration instead of lightweight supervisor routing
- PostgreSQL + authentication + role-based access
- P&ID computer vision parsing
- notification delivery via email / Firebase / WebSocket
- SAP / QMS / CMMS integration

## Recommendation for final pitch

Use the phrase:

> “We did not build just a chatbot. We built a unified industrial memory and reasoning layer that connects documents, failures, compliance, and operational decisions.”

That framing makes the project sound much bigger, more strategic, and more judge-friendly.
