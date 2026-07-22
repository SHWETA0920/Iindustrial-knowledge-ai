# Industrial Knowledge Intelligence — Full Project

Build for ET AI Hackathon 2026, Problem Statement 8. This project delivers a unified AI-powered platform that transforms fragmented industrial documents into actionable operational intelligence.

## Overview

```
industrial-knowledge-copilot/
├── data/                     ← put your documents here (PDF, DOCX, XLSX, CSV, PNG/JPG scans)
├── src/
│   ├── ingest.py             ← Module 1: multi-format ingestion + OCR
│   ├── extract_entities.py   ← Module 2/3: entity extraction + metadata
│   ├── knowledge_graph.py    ← Module 4: NetworkX knowledge graph + queries + JSON export
│   ├── query.py              ← Module 5: multi-query expansion + reranked RAG + confidence scoring
│   ├── rca_agent.py          ← Module 6/9: RCA agent + recurring pattern detection
│   ├── compliance_agent.py   ← Module 8: compliance gap detection + auto-draft
│   ├── risk_prediction.py    ← Failure risk scoring (rule-based)
│   └── evaluation.py         ← Retrieval accuracy / response benchmarking
├── templates/
│   └── index.html            ← Dashboard with chat UI, graph explorer, risk & evaluation panels
├── app.py                    ← Flask API backend
├── outputs_store/            ← Generated outputs (index, entities, graph, metrics)
├── requirements.txt
└── .env.example
```

## Key Modules

| Module                        | Description                                                       |
| ----------------------------- | ----------------------------------------------------------------- |
| Knowledge Graph Visualization | Interactive graph explorer for equipment, failures, and documents |
| Confidence Scoring            | 0–100 score for every answer based on relevance and evidence      |
| Failure Risk Prediction       | Rule-based scoring using frequency, severity, and recency         |
| Advanced Dashboard            | Unified UI with 7 functional tabs                                 |
| Evaluation Metrics            | Measures retrieval accuracy and response time                     |

---

## Important Notes

### Evaluation Module

Replace placeholder questions in:

```
outputs_store/eval_questions.json
```

with real domain-specific queries before demo.

### Risk Prediction

This module is **rule-based**, not ML-based. It combines:

* Failure frequency
* Recency
* Severity keywords
* Pattern recurrence

---

## Design Choices

| Feature   | Implementation   | Reason                                     |
| --------- | ---------------- | ------------------------------------------ |
| Graph DB  | NetworkX         | Lightweight, no external setup             |
| Dashboard | Flask + HTML     | Faster development, no frontend build      |
| Agents    | Python functions | Simpler than full orchestration frameworks |
| Alerts    | In-dashboard     | No external dependencies                   |
| Auth/DB   | Not included     | Focus on core judging criteria             |

---

## Setup

### 1. Environment Setup

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. OCR Dependencies (Optional)

```bash
# Ubuntu
sudo apt-get install tesseract-ocr poppler-utils

# Mac
brew install tesseract poppler
```

### 3. API Key Setup

* Copy `.env.example` → `.env`
* Add your Groq API key

### 4. Add Documents

Place files in:

```
data/
```

---

## Running the Pipeline

```bash
python src/ingest.py
python src/extract_entities.py
python src/knowledge_graph.py
python app.py
```

Open:

```
http://localhost:5000
```

---

## Features in Dashboard

* Expert Copilot (RAG-based Q&A)
* RCA Agent
* Compliance Checker
* Knowledge Graph Explorer
* Risk Prediction Panel
* Alerts System
* Evaluation Metrics

---

## CLI Usage

```bash
python src/query.py "your question"
python src/rca_agent.py "equipment tag"
python src/compliance_agent.py file.txt "topic"
python src/risk_prediction.py "equipment"
python src/evaluation.py
```

---

## Demo Strategy

1. Ask a covered question → show cited answer + high confidence
2. Ask unknown question → show safe fallback
3. Run RCA → show pattern detection
4. Show compliance gap detection
5. Open knowledge graph → visualize relationships
6. Show risk ranking
7. Show alerts
8. Show evaluation metrics

---

## Sample Data Suggestion

Use synthetic dataset:

* Maintenance logs (repeated failures)
* Safety guidelines (PDF)
* SOP documents (DOCX)

---

## Troubleshooting

* OCR errors → install system dependencies
* Slow extraction → reduce document size
* Empty graph → ensure entity extraction worked
* Browser errors → check CORS setup

---

## Conclusion

Industrial Knowledge Intelligence provides a unified AI-powered system for:

* Document understanding
* Root cause analysis
* Compliance validation
* Risk prediction
* Knowledge graph insights

Designed for rapid deployment and effective industrial decision-making.
